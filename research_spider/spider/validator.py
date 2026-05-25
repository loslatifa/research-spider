# spider/validator.py - CSV validation helpers.

import pandas as pd
import os

def validate_csv(file_path):
    """
    Load a CSV file and run basic validation:
    - Check whether the file exists.
    - Check whether it is empty.
    - Show the first rows for quick manual inspection.
    - Show column metadata and null counts.
    """
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return

    try:
        df = pd.read_csv(file_path)
        if df.empty:
            print(f"⚠️ CSV file {file_path} is empty.")
            return

        print(f"✅ CSV loaded successfully: {file_path}")
        print(f"Shape: {df.shape}")
        print("\nColumns:")
        print(df.columns.tolist())

        print("\nFirst 5 rows:")
        print(df.head())

        print("\nNull values per column:")
        print(df.isnull().sum())

    except Exception as e:
        print(f"❌ Error validating CSV {file_path}: {e}")
