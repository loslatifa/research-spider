# spider/validator.py - 数据验证模块

import pandas as pd
import os

def validate_csv(file_path):
    """
    加载 CSV 文件并执行基本验证：
    - 文件是否存在
    - 是否为空
    - 显示前几行进行人工快速验证
    - 显示列信息和空值情况
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
