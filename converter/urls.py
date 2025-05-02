from django.urls import path
from . import views

urlpatterns = [
     path('', views.upload_file, name='upload_file'),
      path('upload/', views.upload_file, name='upload_file'),
    path('preview/<int:file_id>/', views.preview_file, name='preview_file'),
    path('generate/<int:file_id>/', views.generate_script, name='generate_script'),
    path('download/<str:filename>/', views.download_script, name='download_script'),  # <-- Add this line
    path('validate/<int:file_id>/', views.validate_file, name='validate_file'), 
]
