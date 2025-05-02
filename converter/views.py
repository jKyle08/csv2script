import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from .forms import UploadFileForm
from .models import UploadedFile
import os
from django.conf import settings
from django.http import HttpResponse, FileResponse, Http404

def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = form.save()
            return redirect('preview_file', file_id=uploaded.id)
    else:
        form = UploadFileForm()
    return render(request, 'converter/upload.html', {'form': form})


def preview_file(request, file_id):
    uploaded = get_object_or_404(UploadedFile, id=file_id)
    file_path = uploaded.file.path
    selected_sheet = request.GET.get('sheet') or uploaded.sheet_name
    trim = request.GET.get('trim') == 'on'
    preview_data = []
    sheet_names = []
    column_types = {}

    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path, nrows=50)
        elif file_path.endswith(('.xls', '.xlsx')):
            sheet_names = pd.ExcelFile(file_path).sheet_names
            selected_sheet = selected_sheet or sheet_names[0]
            df = pd.read_excel(file_path, sheet_name=selected_sheet, nrows=50)
        else:
            raise ValueError("Unsupported file type")

        uploaded.sheet_name = selected_sheet
        uploaded.save(update_fields=["sheet_name"])

        if trim:
            df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

        column_types = {
            col: pd.api.types.infer_dtype(df[col], skipna=True) for col in df.columns
        }

        preview_data = df.to_dict(orient='records')
        columns = df.columns.tolist()
    except Exception as e:
        return render(request, 'converter/preview.html', {
            'error': str(e), 'file': uploaded
        })

    return render(request, 'converter/preview.html', {
        'columns': columns,
        'rows': preview_data,
        'file': uploaded,
        'sheet_names': sheet_names,
        'selected_sheet': selected_sheet,
        'trim': trim,
        'column_types': column_types
    })

@csrf_exempt
def validate_file(request, file_id):
    uploaded = get_object_or_404(UploadedFile, id=file_id)
    file_path = uploaded.file.path
    selected_sheet = uploaded.sheet_name or None
    required_columns = request.POST.getlist('required_columns')
    errors = []

    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    elif file_path.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(file_path, sheet_name=selected_sheet)
    else:
        return render(request, 'converter/preview.html', {
            'error': 'Unsupported file format.',
            'file': uploaded
        })

    column_types = {
        col: pd.api.types.infer_dtype(df[col], skipna=True) for col in df.columns
    }

    # Validation logic
    for idx, row in df.iterrows():
        row_errors = {}
        for col in required_columns:
            if pd.isnull(row[col]) or (isinstance(row[col], str) and not row[col].strip()):
                row_errors[col] = 'Required field is missing.'

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

        errors.append(row_errors)

    preview_data = df.to_dict(orient='records')

    return render(request, 'converter/validation_result.html', {
        'columns': df.columns,
        'rows': preview_data,
        'errors': errors,
        'file': uploaded,
        'column_types': column_types
    })

DOWNLOAD_PATH = os.path.join(settings.BASE_DIR, 'converter', 'downloads')
@csrf_exempt
def generate_script(request, file_id):
    uploaded = get_object_or_404(UploadedFile, id=file_id)
    file_path = uploaded.file.path
    selected_sheet = uploaded.sheet_name or None
    output_format = request.POST.get('format', 'sql')

    if not os.path.exists(DOWNLOAD_PATH):
        os.makedirs(DOWNLOAD_PATH)

    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    elif file_path.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(file_path, sheet_name=selected_sheet)
    else:
        return HttpResponse("Unsupported file format.", status=400)

    script = ""
    extension = output_format

    if output_format == 'sql':
        table_name = 'your_table_name'
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
        for _, row in df.iterrows():
            values = ', '.join([
                f"'{str(v).replace('\'', '\'\'')}'" if pd.notna(v) else "NULL"
                for v in row
            ])
            script += f"INSERT INTO {table_name} VALUES ({values});\n"


    elif output_format == 'orm':
        model_name = 'YourModel'
        for _, row in df.iterrows():
            fields = ', '.join([
                f"{k}='{str(v).replace('\'', '\'\'')}'"
                for k, v in row.items() if pd.notna(v)
            ])
            script += f"{model_name}.objects.create({fields})\n"

    elif output_format == 'json':
        script = df.to_json(orient='records', indent=2)

    # Save to file
    filename = f"migration_output_{file_id}.{extension}"
    file_save_path = os.path.join(DOWNLOAD_PATH, filename)
    with open(file_save_path, 'w', encoding='utf-8') as f:
        f.write(script)

    return render(request, 'converter/generated_script.html', {
    'script': script,
    'format': output_format,
    'download_url': f"/converter/download/{filename}",
    'file': uploaded,  # <-- add this line
})

def download_script(request, filename):
    file_path = os.path.join(DOWNLOAD_PATH, filename)
    print("DEBUG: Looking for file at:", file_path)
    print("DEBUG: Exists?", os.path.exists(file_path))
    if not os.path.exists(file_path):
        return HttpResponse("File not found.", status=404)
    try:
        with open(file_path, 'rb') as f:
            response = FileResponse(f, as_attachment=True, filename=filename)
            return response
    except Exception as e:
        raise Http404(f"Error opening file: {e}")


