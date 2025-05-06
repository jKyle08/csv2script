import os
import pandas as pd

def parse_file(file_path, sheet_name=None, trim_whitespace=False):
    ext = os.path.splitext(file_path)[-1].lower()
    try:
        if ext in ['.xls', '.xlsx']:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        elif ext == '.csv':
            df = pd.read_csv(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        if df.empty:
            print("Parsed DataFrame is empty.", flush=True)

        if trim_whitespace:
            df.columns = df.columns.str.strip()
            df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

        return df
    except Exception as e:
        print(f"Error parsing file: {e}", flush=True)
        return None


def get_sheet_names(file_path):
    """
    Returns a list of sheet names if the file is Excel.
    Returns an empty list for CSV.
    """
    ext = os.path.splitext(file_path)[-1].lower()
    if ext not in ['.xls', '.xlsx']:
        return []
    try:
        return pd.ExcelFile(file_path).sheet_names
    except Exception as e:
        print(f"Error getting sheet names: {e}")
        return []

def infer_column_types(df):
    """
    Infers and returns a dictionary of column types: 'str', 'int', 'float', 'date', etc.
    """
    column_types = {}
    for col in df.columns:
        dtype = df[col].dtype
        if pd.api.types.is_string_dtype(dtype):
            column_types[col] = 'str'
        elif pd.api.types.is_integer_dtype(dtype):
            column_types[col] = 'int'
        elif pd.api.types.is_float_dtype(dtype):
            column_types[col] = 'float'
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            column_types[col] = 'date'
        else:
            column_types[col] = 'unknown'
    return column_types
