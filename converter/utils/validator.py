import pandas as pd

def validate_required_fields(df, required_columns):
    missing_fields = {}
    for idx, row in df.iterrows():
        row_errors = {}
        for col in required_columns:
            if pd.isnull(row[col]) or (isinstance(row[col], str) and not row[col].strip()):
                row_errors[col] = 'Required field is missing.'
        if row_errors:
            missing_fields[idx] = row_errors
    return missing_fields

def validate_data_types(df):
    column_types = {col: pd.api.types.infer_dtype(df[col], skipna=True) for col in df.columns}
    type_errors = {}
    for idx, row in df.iterrows():
        row_errors = {}
        for col in df.columns:
            val = row[col]
            inferred = column_types[col]
            if not pd.isnull(val):
                if inferred == 'integer' and not isinstance(val, (int, float)):
                    row_errors[col] = 'Expected number.'
                elif inferred == 'string' and not isinstance(val, str):
                    row_errors[col] = 'Expected string.'
                elif inferred == 'datetime' and not pd.api.types.is_datetime64_any_dtype(type(val)):
                    row_errors[col] = 'Expected date.'
        if row_errors:
            type_errors[idx] = row_errors
    return column_types, type_errors

def validate_no_duplicates(df, unique_columns):
    duplicate_errors = {}
    if unique_columns:
        dupes = df[df.duplicated(subset=unique_columns, keep=False)]
        for idx in dupes.index:
            duplicate_errors[idx] = {col: 'Duplicate value.' for col in unique_columns}
    return duplicate_errors

def merge_row_errors(*error_dicts):
    merged = []
    all_indices = set()
    for d in error_dicts:
        all_indices.update(d.keys())

    for idx in sorted(all_indices):
        row_errors = {}
        for d in error_dicts:
            row_errors.update(d.get(idx, {}))
        merged.append(row_errors)
    return merged

def validate_file(file_path, required_columns, unique_columns, selected_sheet=None):
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    elif file_path.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(file_path, sheet_name=selected_sheet)
    else:
        raise ValueError("Unsupported file format.")

    df.fillna('', inplace=True)  # Optional: replace NaN with empty string for rendering

    # Perform validations
    missing_fields = validate_required_fields(df, required_columns)
    column_types, type_errors = validate_data_types(df)
    duplicate_errors = validate_no_duplicates(df, unique_columns)

    # Merge all errors row-wise
    errors = merge_row_errors(missing_fields, type_errors, duplicate_errors)

    # Build rows as list of dicts
    rows = df.to_dict(orient='records')
    columns = list(df.columns)

    return {
        'rows': rows,
        'errors': errors,
        'columns': columns,
        'column_types': column_types
    }
