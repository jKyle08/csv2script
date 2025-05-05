import pandas as pd

def generate_sql_script(df, table_name):
    """
    Generates SQL INSERT statements from a DataFrame.
    Assumes all columns map directly to table columns in order.
    """
    statements = []
    for _, row in df.iterrows():
        values = ', '.join([
            f"""'{str(val).replace("'", "''").replace(" - ", "-")}'""" if pd.notna(val) else "NULL"
            for val in row
        ])
        statements.append(f"INSERT INTO {table_name} VALUES ({values});")
    return '\n'.join(statements)


def generate_orm_script(df, model_name):
    """
    Generates Django ORM create statements from a DataFrame.
    Maps each column to a model field by name.
    """
    statements = []
    for _, row in df.iterrows():
        fields = ', '.join([
            f"""{col}='{str(val).replace("'", "''").replace(" - ", "-")}'"""
            for col, val in row.items() if pd.notna(val)
        ])

        statements.append(f"{model_name}.objects.create({fields})")
    return '\n'.join(statements)


def generate_json_script(df):
    """
    Converts a DataFrame to a pretty-printed JSON array of records.
    """
    records = df.to_dict(orient='records')
    
    # Remove spaces around dashes in string values
    for record in records:
        for key, value in record.items():
            if isinstance(value, str):
                record[key] = value.replace(" - ", "-")
    
    import json
    return json.dumps(records, indent=2)
