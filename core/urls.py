from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/upload/', views.upload_question_bank, name='upload_question_bank'),
    path('teacher/delete/<int:id>/', views.delete_question_bank, name='delete_question_bank'),
    path('exam/', views.exam_dashboard, name='exam_dashboard'),
    path('exam/download/<int:id>/', views.download_question_bank, name='download_question_bank'),
    path('exam/generate/', views.generate_question_paper, name='generate_question_paper'),  # New URL
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('view/<int:paper_id>/', views.view_question_paper, name='view_question_paper'),
    path('edit/<int:paper_id>/', views.edit_question_paper, name='edit_question_paper'),
    path('export/<int:paper_id>/', views.export_pdf, name='export_pdf'),
]