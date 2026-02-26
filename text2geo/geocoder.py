"""
Core geocoder engine for text2geo.

Builds an in-memory index of place names (including alternate/localized names)
and provides exact + fuzzy lookup via rapidfuzz.
"""

from typing import Optional

import pandas as pd
from rapidfuzz import process, fuzz

from text2geo.data import get_data_path, is_downloaded, download
from text2geo.exceptions import DatasetNotFoundError


class Geocoder:
    """
    Offline fuzzy geocoder backed by GeoNames data.

    Args:
        dataset:       One of 'ru', 'cis', 'world'. Default: 'cis'.
        data_dir:      Custom data directory. Default: ~/.text2geo/data
        auto_download: If True, automatically download the dataset if missing.
        csv_path:      Direct path to a pre-built CSV (overrides dataset/data_dir).

    Examples:
        >>> geo = Geocoder(dataset="cis")
        >>> geo.geocode("Москва")
        {'name': 'Moscow', 'lat': 55.75222, 'lon': 37.61556, ...}

        >>> geo.geocode("Масква")  # typo → still finds Moscow
        {'name': 'Moscow', 'lat': 55.75222, 'lon': 37.61556, 'score': 90, ...}
    """

    def __init__(
        self,
        dataset: str = "cis",
        data_dir: Optional[str] = None,
        auto_download: bool = True,
        csv_path: Optional[str] = None,
    ):
        if csv_path:
            path = csv_path
        else:
            if not is_downloaded(dataset, data_dir):
                if auto_download:
                    download(dataset, data_dir=data_dir)
                else:
                    raise DatasetNotFoundError(
                        dataset, str(data_dir or get_data_path(dataset).parent)
                    )
            path = str(get_data_path(dataset, data_dir))

        self._dataset = dataset
        self._df = pd.read_csv(path, low_memory=False)
        self._df["alternatenames"] = self._df["alternatenames"].fillna("")
        self._name_to_indices: dict[str, list[int]] = {}
        self._build_index()

    @property
    def size(self) -> int:
        """Number of places in the loaded dataset."""
        return len(self._df)

    @property
    def dataset(self) -> str:
        """Name of the loaded dataset."""
        return self._dataset

    def geocode(
        self,
        query: str,
        country: Optional[str] = None,
        threshold: int = 75,
        top_n: int = 1,
    ) -> Optional[dict | list[dict]]:
        """
        Convert a place name to geographic coordinates.

        Args:
            query:     Place name in any language (e.g. "Москва", "Moscow").
            country:   ISO-3166 country filter, e.g. "RU", "UA", "KZ".
            threshold: Minimum fuzzy match score (0–100). Default: 75.
            top_n:     Number of results to return. 1 returns a dict, >1 a list.

        Returns:
            A dict with keys: geonameid, name, lat, lon, country, population, score.
            Returns None if no match found above the threshold.
        """
        query_lower = query.strip().lower()
        if not query_lower:
            return None

        if query_lower in self._name_to_indices:
            result = self._exact_match(query_lower, country, top_n)
            if result is not None:
                return result

        return self._fuzzy_match(query_lower, country, threshold, top_n)

    def geocode_batch(
        self,
        queries: list[str],
        country: Optional[str] = None,
        threshold: int = 75,
    ) -> list[dict]:
        """
        Geocode a list of place names at once.

        Args:
            queries:   List of place name strings.
            country:   Optional country filter applied to all queries.
            threshold: Minimum fuzzy match score.

        Returns:
            List of result dicts (one per query). Failed lookups contain
            'error': 'not found' with lat/lon set to None.
        """
        results = []
        for q in queries:
            result = self.geocode(q, country=country, threshold=threshold)
            if result is None:
                results.append({
                    "query": q, "name": None,
                    "lat": None, "lon": None, "error": "not found",
                })
            else:
                result["query"] = q
                results.append(result)
        return results

    def _build_index(self) -> None:
        for idx, row in self._df.iterrows():
            names = set()
            names.add(row["name"].lower())
            if pd.notna(row.get("asciiname")):
                names.add(row["asciiname"].lower())
            if row["alternatenames"]:
                for alt in str(row["alternatenames"]).split(","):
                    stripped = alt.strip().lower()
                    if stripped:
                        names.add(stripped)
            for n in names:
                if n:
                    self._name_to_indices.setdefault(n, []).append(idx)

        self._all_names = list(self._name_to_indices.keys())

    def _exact_match(
        self, query_lower: str, country: Optional[str], top_n: int
    ) -> Optional[dict | list[dict]]:
        indices = self._name_to_indices[query_lower]
        candidates = self._df.iloc[indices].copy()
        if country:
            candidates = candidates[
                candidates["country_code"] == country.upper()
            ]
        if candidates.empty:
            return None
        return self._format(candidates, score=100, top_n=top_n)

    def _fuzzy_match(
        self,
        query_lower: str,
        country: Optional[str],
        threshold: int,
        top_n: int,
    ) -> Optional[dict | list[dict]]:
        matches = process.extract(
            query_lower, self._all_names, scorer=fuzz.WRatio, limit=20
        )

        seen: set[int] = set()
        candidates = []

        for match_name, score, _ in matches:
            if score < threshold:
                continue
            for idx in self._name_to_indices[match_name]:
                if idx in seen:
                    continue
                seen.add(idx)
                row = self._df.iloc[idx]
                if country and row["country_code"] != country.upper():
                    continue
                candidates.append({
                    "geonameid": int(row["geonameid"]),
                    "name": row["name"],
                    "lat": row["latitude"],
                    "lon": row["longitude"],
                    "country": row["country_code"],
                    "population": int(row["population"]),
                    "score": int(score),
                    "matched_as": match_name,
                })

        if not candidates:
            return None

        candidates.sort(key=lambda x: (-x["score"], -x["population"]))

        if top_n == 1:
            return candidates[0]
        return candidates[:top_n]

    def _format(
        self, candidates: pd.DataFrame, score: int, top_n: int
    ) -> dict | list[dict]:
        candidates = candidates.sort_values("population", ascending=False)
        results = []
        for _, row in candidates.head(top_n).iterrows():
            results.append({
                "geonameid": int(row["geonameid"]),
                "name": row["name"],
                "lat": row["latitude"],
                "lon": row["longitude"],
                "country": row["country_code"],
                "population": int(row["population"]),
                "score": score,
            })
        if top_n == 1:
            return results[0]
        return results

    def __repr__(self) -> str:
        return f"Geocoder(dataset='{self._dataset}', places={self.size:,})"
