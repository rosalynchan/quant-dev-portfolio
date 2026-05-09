"""
Utility functions for loading trading data from multiple file formats.

Supports: CSV, Parquet, Excel (.xlsx, .xls)

Usage:
    from src.tools.data_loader import load_data

    df, metadata = load_data("data/sample_ticks.csv")
    print(f"Loaded {metadata['rows']} rows")
"""

from __future__ import annotations
from pathlib import Path
import pandas as pd


def _detect_format(file_path: str) -> str:
    """
    Detect file format from extension.

    :param: file_path: Path to the file.

    :returns: format string: "csv", "parquet", or "excel".

    Raises: ValueError: If format is not supported.

    TODO: 
    
        1. Convert file_path to a Path object
        2. Get the file suffix (extension) in lowercase: .suffix.lower()
        3. Match against: ".csv", ".parquet", ".xlsx", ".xls"
        4. Return the format string (without the dot)
        5. If format not recognised, raise ValueError with a clear message
    """
    pass


def _read_csv(file_path: str) -> pd.DataFrame:
    """
    Read CSV file into DataFrame.

    TODO:
    
        1. Use pd.read_csv(file_path)
        2. That's it — return the DataFrame
    """
    pass


def _read_parquet(file_path: str) -> pd.DataFrame:
    """
    Read Parquet file into DataFrame.

    TODO:
    
        1. Use pd.read_parquet(file_path)
        2. Return the DataFrame
    """
    pass


def _read_excel(file_path: str) -> pd.DataFrame:
    """
    Read Excel file into DataFrame.

    TODO:
    
        1. Use pd.read_excel(file_path)
        2. Return the DataFrame
    """
    pass


def load_data(file_path: str) -> tuple[pd.DataFrame, dict]:
    """
    Load data from file and extract metadata.

    :param: file_path: Path to CSV, Parquet, or Excel file.

    :returns: tuple of (DataFrame, metadata dict). Metadata dict contains:
            - rows: number of rows
            - columns: list of column names
            - dtypes: dict of {col: dtype}
            - memory_usage_mb: estimated memory usage
            - file_format: detected format ("csv", "parquet", "excel")

    :raises:
        FileNotFoundError: If file does not exist.
        ValueError: If format not supported.
        Exception: If file is corrupted or unreadable.

    TODO:
    
        1. Check if file exists using Path(file_path).exists()
           - If not, raise FileNotFoundError
        2. Detect format using _detect_format(file_path)
        3. Load the DataFrame:
           - If format is "csv", call _read_csv()
           - If "parquet", call _read_parquet()
           - If "excel", call _read_excel()
        4. Build metadata dict:
           - rows: len(df)
           - columns: df.columns.tolist()
           - dtypes: df.dtypes.to_dict() (converts to {col: dtype_str})
           - memory_usage_mb: df.memory_usage(deep=True).sum() / 1024 / 1024
           - file_format: the detected format
        5. Return (df, metadata)
    """
    pass