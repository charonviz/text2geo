"""
Data download and management for text2geo.

Downloads GeoNames dumps and prepares them for offline geocoding.
"""

import os
import sys
import zipfile
import urllib.request
from pathlib import Path
from typing import Optional

import pandas as pd

from text2geo.exceptions import InvalidDatasetError, DownloadError

GEONAMES_BASE_URL = "https://download.geonames.org/export/dump/"

GEONAMES_COLUMNS = [
    "geonameid", "name", "asciiname", "alternatenames",
    "latitude", "longitude", "feature_class", "feature_code",
    "country_code", "cc2", "admin1", "admin2", "admin3", "admin4",
    "population", "elevation", "dem", "timezone", "modification_date",
]

KEEP_COLUMNS = [
    "geonameid", "name", "asciiname", "alternatenames",
    "latitude", "longitude", "feature_code",
    "country_code", "population", "timezone",
]

DATASETS = {
    "ru": {
        "description": "Russia only",
        "countries": ["RU"],
    },
    "cis": {
        "description": "CIS + former USSR countries",
        "countries": [
            "RU", "UA", "BY", "KZ", "UZ", "TJ",
            "KG", "TM", "AZ", "AM", "GE", "MD",
        ],
    },
    "world": {
        "description": "All cities worldwide (population > 1000)",
        "source": "cities1000.zip",
    },
}


def _default_data_dir() -> Path:
    return Path.home() / ".text2geo" / "data"


def available_datasets() -> dict:
    """Return a dictionary of available dataset names and their descriptions."""
    return {name: info["description"] for name, info in DATASETS.items()}


def is_downloaded(dataset: str, data_dir: Optional[str] = None) -> bool:
    """Check whether a dataset has already been downloaded."""
    _validate_dataset(dataset)
    path = Path(data_dir) if data_dir else _default_data_dir()
    return (path / f"{dataset}.csv").exists()


def download(
    dataset: str = "cis",
    data_dir: Optional[str] = None,
    verbose: bool = True,
) -> Path:
    """
    Download and prepare a GeoNames dataset.

    Args:
        dataset:  One of 'ru', 'cis', 'world'.
        data_dir: Directory to store data. Default: ~/.text2geo/data
        verbose:  Print progress information.

    Returns:
        Path to the resulting CSV file.
    """
    _validate_dataset(dataset)
    dest = Path(data_dir) if data_dir else _default_data_dir()
    dest.mkdir(parents=True, exist_ok=True)
    output_path = dest / f"{dataset}.csv"

    if output_path.exists():
        if verbose:
            print(f"Dataset '{dataset}' already exists at {output_path}")
        return output_path

    info = DATASETS[dataset]
    tmp_dir = dest / "tmp"
    tmp_dir.mkdir(exist_ok=True)

    if dataset == "world":
        df = _download_world(info, tmp_dir, verbose)
    else:
        df = _download_countries(info["countries"], tmp_dir, verbose)

    df.to_csv(output_path, index=False, encoding="utf-8")

    _cleanup_tmp(tmp_dir)

    if verbose:
        print(f"Saved {len(df):,} places to {output_path}")
        print(f"File size: {output_path.stat().st_size / 1024 / 1024:.1f} MB")

    return output_path


def _download_world(info: dict, tmp_dir: Path, verbose: bool) -> pd.DataFrame:
    source = info["source"]
    zip_path = tmp_dir / source
    txt_name = source.replace(".zip", ".txt")
    txt_path = tmp_dir / txt_name

    if not txt_path.exists():
        _fetch(f"{GEONAMES_BASE_URL}{source}", zip_path, verbose)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extract(txt_name, tmp_dir)
        zip_path.unlink(missing_ok=True)

    return _load_txt(txt_path)


def _download_countries(
    country_codes: list[str], tmp_dir: Path, verbose: bool
) -> pd.DataFrame:
    frames = []
    for code in country_codes:
        txt_path = tmp_dir / f"{code}.txt"
        if not txt_path.exists():
            zip_path = tmp_dir / f"{code}.zip"
            _fetch(f"{GEONAMES_BASE_URL}{code}.zip", zip_path, verbose)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extract(f"{code}.txt", tmp_dir)
            zip_path.unlink(missing_ok=True)
        frames.append(_load_txt(txt_path))
    return pd.concat(frames, ignore_index=True)


def _load_txt(path: Path) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        sep="\t",
        header=None,
        names=GEONAMES_COLUMNS,
        low_memory=False,
        dtype={"admin1": str, "admin2": str, "admin3": str, "admin4": str},
    )
    df = df[df["feature_class"] == "P"]
    return df[KEEP_COLUMNS]


def _fetch(url: str, dest: Path, verbose: bool) -> None:
    if verbose:
        print(f"  Downloading {url} ...")
    try:
        urllib.request.urlretrieve(url, dest)
    except Exception as e:
        raise DownloadError(f"Failed to download {url}: {e}") from e


def _cleanup_tmp(tmp_dir: Path) -> None:
    for f in tmp_dir.iterdir():
        f.unlink(missing_ok=True)
    tmp_dir.rmdir()


def _validate_dataset(dataset: str) -> None:
    if dataset not in DATASETS:
        raise InvalidDatasetError(dataset, list(DATASETS.keys()))


def get_data_path(dataset: str, data_dir: Optional[str] = None) -> Path:
    """Return the expected CSV path for a dataset."""
    _validate_dataset(dataset)
    dest = Path(data_dir) if data_dir else _default_data_dir()
    return dest / f"{dataset}.csv"


if __name__ == "__main__":
    ds = sys.argv[1] if len(sys.argv) > 1 else "cis"
    data_path = sys.argv[2] if len(sys.argv) > 2 else None
    download(ds, data_dir=data_path)
