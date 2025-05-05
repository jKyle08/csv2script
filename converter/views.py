import os
import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.http import HttpResponse, FileResponse, Http404, JsonResponse
from django.urls import reverse
from django.template.loader import render_to_string

from .forms import UploadFileForm
from .models import UploadedFile
from .utils.file_parser import parse_file, get_sheet_names, infer_column_types
from .utils.validator import validate_file
from .utils.script_generator import generate_sql_script, generate_orm_script, generate_json_script

DOWNLOAD_PATH = os.path.join(settings.BASE_DIR, 'converter', 'downloads')

def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.save()
            file_path = uploaded_file.file.path
            extension = os.path.splitext(file_path)[1].lower()

            if extension in ['.xls', '.xlsx']:
                # Get the sheet names from the uploaded file
                sheet_names = get_sheet_names(file_path)
                base_name = os.path.basename(uploaded_file.file.name).rsplit('_', 1)[0]

                # If there are multiple sheets, return modal HTML with sheet options
                if len(sheet_names) > 1:
                    modal_html = render_to_string('converter/select_sheet_modal.html', {
                        'file': uploaded_file,
                        'base_name': base_name,
                        'sheets': sheet_names
                    }, request=request)

                    return JsonResponse({
                        'show_modal': True,
                        'modal_html': modal_html
                    })

                # If there's only one sheet, we can directly proceed to the preview
                else:
                    # Process the file with the sheet selected
                    sheet_name = sheet_names[0]
                    return JsonResponse({
                        'redirect_url': reverse('preview_file', kwargs={'file_id': uploaded_file.id, 'sheet_name': sheet_name})
                    })

            return JsonResponse({'error': 'Unsupported file format'}, status=400)

        return JsonResponse({'error': 'Invalid form submission'}, status=400)

    # Fallback for GET request or if something went wrong
    return render(request, 'converter/upload.html', {'form': UploadFileForm()})


# Select sheet and parse the selected sheet for preview
def select_sheet(request, file_id):
    uploaded_file = get_object_or_404(UploadedFile, id=file_id)

    # Clean base name for display
    original_name = os.path.basename(uploaded_file.file.name)  # e.g., 'Facility_xls_RnCmDxI.xlsx'
    base_name = original_name.rsplit('_', 1)[0]  # e.g., 'Facility_xls'

    file_path = uploaded_file.file.path

    if request.method == 'POST':
        sheet_name = request.POST.get('sheet_name')
        if not sheet_name:
            return HttpResponse("No sheet selected", status=400)

        try:
            # Parse the selected sheet using pandas
            excel_file = pd.ExcelFile(file_path)
            df = excel_file.parse(sheet_name)
            
            # Optionally, render the data frame for preview
            return render(request, 'converter/preview.html', {'df': df, 'file': uploaded_file})
        except Exception as e:
            return HttpResponse(f"Error parsing sheet: {str(e)}", status=500)

    else:
        # Handle sheet names in GET request (for rendering modal or page)
        sheet_names = get_sheet_names(file_path)

        context = {
            'file': uploaded_file,
            'base_name': base_name,
            'sheets': sheet_names
        }

        # Handle AJAX modal request
        if request.GET.get('modal') == 'true':
            return render(request, 'converter/select_sheet_modal.html', context)

        # Fallback full-page view (if needed)
        return render(request, 'converter/sheet_select.html', context)

def preview_file(request, file_id):
    uploaded = get_object_or_404(UploadedFile, id=file_id)
    file_path = uploaded.file.path
    selected_sheet = request.GET.get('sheet') or uploaded.sheet_name
    trim = request.GET.get('trim') == 'on'
    preview_data = []
    sheet_names = []
    column_types = {}

    try:
        sheet_names = get_sheet_names(file_path)
        if sheet_names and not selected_sheet:
            selected_sheet = sheet_names[0]

        df = parse_file(file_path, sheet_name=selected_sheet, trim_whitespace=trim)
        if df is None:
            raise ValueError("Unable to parse file")

        uploaded.sheet_name = selected_sheet
        uploaded.save(update_fields=["sheet_name"])

        column_types = infer_column_types(df)
        preview_data = df.head(50).to_dict(orient='records')
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
def validate_file_view(request, file_id):
    # Get the uploaded file object using the file_id
    uploaded = get_object_or_404(UploadedFile, id=file_id)
    file_path = uploaded.file.path
    selected_sheet = uploaded.sheet_name or None

    # Get the required and unique columns from the POST request
    required_columns = request.POST.getlist('required_columns')
    unique_columns = request.POST.getlist('unique_columns')

    try:
        # Call the validate_file function from validator.py to validate the file
        errors = validate_file(file_path, required_columns, unique_columns, selected_sheet)

        # If errors are found, render the validation result with the errors
        return render(request, 'converter/validation_result.html', {
            'rows': errors['rows'],
            'errors': errors['errors'],
            'columns': errors['columns'],
            'column_types': errors['column_types'],
            'file': uploaded,
        })

    except Exception as e:
        # In case of any exception (e.g., file parsing errors), show an error message
        return render(request, 'converter/validation_result.html', {
            'error': str(e),
            'file': uploaded,
            'rows': [],
            'errors': [],
            'columns': [],
            'column_types': {},
        })


@csrf_exempt
def generate_script(request, file_id):
    # Get the uploaded file object using the file_id
    uploaded = get_object_or_404(UploadedFile, id=file_id)
    file_path = uploaded.file.path
    selected_sheet = uploaded.sheet_name or None
    output_format = request.POST.get('format', 'sql')

    # Ensure the download path exists
    if not os.path.exists(DOWNLOAD_PATH):
        os.makedirs(DOWNLOAD_PATH)

    # Parse the file (implement your parse_file function)
    df = parse_file(file_path, sheet_name=selected_sheet, trim_whitespace=True)
    if df is None:
        return HttpResponse("Failed to parse file.", status=400)

    # Initialize the script variable and output format extension
    script = ""
    extension = output_format

    # Generate the script based on the selected format
    if output_format == 'sql':
        table_name = 'your_table_name'  # Replace with the actual table name
        script = generate_sql_script(df, table_name)

    elif output_format == 'orm':
        model_name = 'YourModel'  # Replace with the actual model name
        script = generate_orm_script(df, model_name)

    elif output_format == 'json':
        script = generate_json_script(df)

    # Save the generated script to a file
    filename = f"migration_output_{file_id}.{extension}"
    file_save_path = os.path.join(DOWNLOAD_PATH, filename)
    with open(file_save_path, 'w', encoding='utf-8') as f:
        f.write(script)

    # Render the result in a template and provide the download link
    return render(request, 'converter/generated_script.html', {
        'script': script,
        'format': output_format,
        'download_url': f"/converter/download/{filename}",
        'file': uploaded,
    })

def download_script(request, filename):
    file_path = os.path.join(DOWNLOAD_PATH, filename)
    if not os.path.exists(file_path):
        return HttpResponse("File not found.", status=404)
    try:
        with open(file_path, 'rb') as f:
            response = FileResponse(f, as_attachment=True, filename=filename)
            return response
    except Exception as e:
        raise Http404(f"Error opening file: {e}")