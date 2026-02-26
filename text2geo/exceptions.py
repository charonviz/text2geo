class Text2GeoError(Exception):
    """Base exception for text2geo."""


class DatasetNotFoundError(Text2GeoError):
    """Raised when the requested dataset has not been downloaded yet."""

    def __init__(self, dataset: str, data_dir: str):
        self.dataset = dataset
        self.data_dir = data_dir
        super().__init__(
            f"Dataset '{dataset}' not found in '{data_dir}'. "
            f"Run: text2geo.download('{dataset}') or: python -m text2geo.data {dataset}"
        )


class InvalidDatasetError(Text2GeoError):
    """Raised when an unknown dataset name is provided."""

    def __init__(self, dataset: str, valid: list[str]):
        self.dataset = dataset
        self.valid = valid
        super().__init__(
            f"Unknown dataset '{dataset}'. Valid options: {', '.join(valid)}"
        )


class DownloadError(Text2GeoError):
    """Raised when a GeoNames file fails to download."""
