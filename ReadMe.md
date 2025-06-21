# CSV/Excel to Script Converter

This Django web application allows users to upload CSV or Excel files, preview their data, validate it, and convert it into SQL insert scripts, Django ORM code, or JSON data.

## Features

- **Upload** CSV (`.csv`) or Excel (`.xls`, `.xlsx`) files.
- **Sheet Selection** for Excel files with multiple sheets.
- **Data Preview** with column type inference and whitespace trimming.
- **Validation** for required/unique columns and data types.
- **Script Generation** in SQL, Django ORM, or JSON formats.
- **Download** the generated script for use in your projects.

## Usage

1. **Install dependencies**  
   Make sure you have Python and Django installed.  
   Install requirements:
   ```sh
   pip install -r requirements.txt
   ```

2. **Run migrations**  
   ```sh
   python manage.py migrate
   ```

3. **Start the server**  
   ```sh
   python manage.py runserver
   ```

4. **Open your browser** and go to [http://localhost:8000/](http://localhost:8000/).

5. **Upload your file**, select a sheet if prompted, preview and validate your data, then generate and download your script.

## Project Structure

- `converter/` – Main Django app with views, models, forms, templates, and static files.
- `core/` – Django project settings and configuration.
- `media/uploads/` – Uploaded files storage.
- `converter/downloads/` – Generated scripts for download.

## Notes

- Only `.csv`, `.xls`, and `.xlsx` files are supported.
- For Excel files, you can select which sheet to process.
- Validation checks for required and unique columns before script generation.

## License

MIT License

---

*Made with Django