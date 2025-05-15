from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import User, QuestionBank, QuestionPaper
from django.http import FileResponse, HttpResponse
from PyPDF2 import PdfReader
import random
import re
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
import os
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)

# Home page
def index(request):
    return render(request, 'index.html')

# Login view
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)
            user.last_login = timezone.now()
            user.save()
            if user.role == 'teacher':
                return redirect('teacher_dashboard')
            elif user.role == 'exam':
                return redirect('exam_dashboard')
            elif user.role == 'admin':
                return redirect('admin_dashboard')
        else:
            messages.error(request, 'Invalid email or password.')
    return render(request, 'login.html')

# Logout view
def logout_view(request):
    logout(request)
    return redirect('index')

# Register view
def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        role = request.POST.get('role')
        
        if not email:
            messages.error(request, 'Email address is required')
            return redirect('register')
            
        try:
            user = User.objects.create_user(username=username, password=password, email=email)
            user.role = role
            user.save()
            messages.success(request, 'User registered successfully.')
            return redirect('login')
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('register')
    return render(request, 'register.html')

# Teacher dashboard
@login_required
def teacher_dashboard(request):
    return render(request, 'teacher_dashboard.html')

# Upload question bank
@login_required
def upload_question_bank(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        module = request.POST.get('module')
        question_file = request.FILES.get('question_file')
        
        if not all([title, module, question_file]):
            messages.error(request, 'Please fill all fields and select a file.')
            return redirect('teacher_dashboard')
            
        try:
            QuestionBank.objects.create(
                title=title,
                module=module,
                question_file=question_file,
                created_by=request.user
            )
            messages.success(request, 'Question bank uploaded successfully!')
            return redirect('teacher_dashboard')
        except Exception as e:
            messages.error(request, f'Error uploading file: {str(e)}')
            return redirect('teacher_dashboard')
    return render(request, 'teacher_dashboard.html')

# Delete question bank
@login_required
def delete_question_bank(request, id):
    question_bank = get_object_or_404(QuestionBank, id=id)
    question_bank.delete()
    messages.success(request, 'Question bank deleted successfully.')
    return redirect('teacher_dashboard')

# Download question bank
@login_required
def download_question_bank(request, id):
    question_bank = get_object_or_404(QuestionBank, id=id)
    file_path = question_bank.question_file.path
    file = open(file_path, 'rb')
    response = FileResponse(file)
    return response

# Exam dashboard
@login_required
def exam_dashboard(request):
    question_banks = QuestionBank.objects.all()
    question_papers = QuestionPaper.objects.filter(created_by=request.user).order_by('-created_at')
    context = {
        'question_banks': question_banks,
        'available_banks': QuestionBank.objects.all(),
        'question_papers': question_papers
    }
    return render(request, 'exam_dashboard.html', context)

# Generate question paper
@login_required
def generate_question_paper(request):
    if request.method == 'POST':
        question_bank_id = request.POST.get('question_bank')
        module_numbers = request.POST.get('module', '').strip()
        questions_per_module = int(request.POST.get('num_questions', 10))

        logger.debug(f"Received question_bank_id: {question_bank_id}")

        try:
            question_bank_id = int(question_bank_id)
        except (ValueError, TypeError):
            messages.error(request, "Invalid question bank selection. Please select a valid question bank.")
            return redirect('exam_dashboard')

        question_bank = get_object_or_404(QuestionBank, id=question_bank_id)
        modules = [f"MODULE-{m.strip()}" for m in module_numbers.split(',') if m.strip().isdigit()]
        
        if not modules:
            messages.error(request, "Please specify valid module numbers.")
            return redirect('exam_dashboard')

        available_questions_by_module = {module: [] for module in modules}
        if question_bank.question_file:
            try:
                pdf_reader = PdfReader(question_bank.question_file.path)
                current_module = None
                current_question = ""
                
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    for line in lines:
                        module_match = re.search(r"(?i)^MODULE\s*[-]?\s*(\d+)\s*:?", line)
                        if module_match:
                            if current_question and current_module in available_questions_by_module:
                                available_questions_by_module[current_module].append(current_question.strip())
                            current_question = ""
                            module_num = module_match.group(1)
                            current_module = f"MODULE-{module_num}"
                            continue
                        
                        if current_module in available_questions_by_module:
                            if line[0].isdigit() and "." in line[:3]:
                                if current_question:
                                    available_questions_by_module[current_module].append(current_question.strip())
                                current_question = line.split(".", 1)[1].strip()
                            elif current_question:
                                current_question += " " + line
                
                if current_question and current_module in available_questions_by_module:
                    available_questions_by_module[current_module].append(current_question.strip())
                
                for module in available_questions_by_module:
                    available_questions_by_module[module] = [
                        q.strip() for q in available_questions_by_module[module] if q and len(q.strip()) > 5
                    ]
                
                logger.debug(f"Available questions by module: {available_questions_by_module}")
            
            except Exception as e:
                messages.error(request, f"Error reading question bank: {str(e)}")
                return redirect('exam_dashboard')

        all_questions = []
        question_module_mapping = []
        available_flat = [q for module_questions in available_questions_by_module.values() for q in module_questions]
        random.shuffle(available_flat)
        
        question_idx = 0
        for module in modules:
            module_questions = available_questions_by_module.get(module, [])
            selected_questions = module_questions[:questions_per_module]
            remaining_needed = questions_per_module - len(selected_questions)
            
            if remaining_needed > 0 and available_flat:
                additional_questions = [q for q in available_flat[question_idx:question_idx + remaining_needed] if q not in selected_questions]
                selected_questions.extend(additional_questions)
                question_idx += remaining_needed
            
            for question in selected_questions:
                question_module_mapping.append((question, module))
            all_questions.extend(selected_questions)
            if len(selected_questions) < questions_per_module:
                messages.warning(request, f"Only {len(selected_questions)} questions available for {module}, expected {questions_per_module}.")

        if len(all_questions) > 0:
            new_paper = QuestionPaper(
                title=f"Question Paper - {question_bank.question_file.name}",
                module=','.join(modules),
                questions=all_questions,
                created_by=request.user,
                question_bank=question_bank,
                status='draft',
                question_module_mapping=question_module_mapping
            )
            new_paper.save()
            messages.success(request, f"Question paper generated with {len(all_questions)} questions.")
            return redirect('view_question_paper', paper_id=new_paper.id)
        else:
            messages.error(request, "No questions available to generate the paper.")
            return redirect('exam_dashboard')

    return redirect('exam_dashboard')

# Admin dashboard
@login_required
def admin_dashboard(request):
    return render(request, 'admin_dashboard.html')

# View question paper
@login_required
def view_question_paper(request, paper_id):
    paper = get_object_or_404(QuestionPaper, id=paper_id)
    modules = paper.module.split(',')
    
    if hasattr(paper, 'question_module_mapping') and paper.question_module_mapping:
        question_module_mapping = paper.question_module_mapping
    else:
        questions_flat = paper.questions.copy()
        question_module_mapping = []
        questions_per_module = len(questions_flat) // len(modules)
        for i, module in enumerate(modules):
            start_idx = i * questions_per_module
            end_idx = (i + 1) * questions_per_module if i < len(modules) - 1 else len(questions_flat)
            for j in range(start_idx, end_idx):
                if j < len(questions_flat):
                    question_module_mapping.append((questions_flat[j], module))
    
    questions_per_module_dict = {module: [] for module in modules}
    for question, module in question_module_mapping:
        if module in questions_per_module_dict:
            questions_per_module_dict[module].append(question)
    
    questions_per_module = [
        {'module': module, 'questions': questions}
        for module, questions in questions_per_module_dict.items()
    ]
    
    context = {
        'paper': paper,
        'questions_per_module': questions_per_module,
    }
    return render(request, 'view_question_paper.html', context)

# Edit question paper
@login_required
def edit_question_paper(request, paper_id):
    paper = get_object_or_404(QuestionPaper, id=paper_id)
    question_bank = paper.question_bank
    modules = paper.module.split(',')
    
    if hasattr(paper, 'question_module_mapping') and paper.question_module_mapping:
        question_module_mapping = paper.question_module_mapping
    else:
        questions_flat = paper.questions.copy()
        question_module_mapping = []
        questions_per_module = len(questions_flat) // len(modules)
        for i, module in enumerate(modules):
            start_idx = i * questions_per_module
            end_idx = (i + 1) * questions_per_module if i < len(modules) - 1 else len(questions_flat)
            for j in range(start_idx, end_idx):
                if j < len(questions_flat):
                    question_module_mapping.append((questions_flat[j], module))
    
    questions_per_module_dict = {module: [] for module in modules}
    for question, module in question_module_mapping:
        if module in questions_per_module_dict:
            questions_per_module_dict[module].append(question)
    
    questions_per_module = [
        {'module': module, 'questions': questions}
        for module, questions in questions_per_module_dict.items()
    ]

    if request.method == 'POST':
        paper.title = request.POST.get('title')
        updated_questions = []
        removed_questions = request.POST.getlist('remove_question')
        
        for question, module in question_module_mapping:
            if question not in removed_questions:
                updated_questions.append((module, question))
        
        for module in modules:
            bank_questions = request.POST.getlist(f'bank_questions_{module}')
            for question in bank_questions:
                if question.strip() and (module, question) not in updated_questions:
                    updated_questions.append((module, question))
        
        final_questions = []
        new_mapping = []
        for module in modules:
            module_questions = [q for m, q in updated_questions if m == module]
            for question in module_questions:
                new_mapping.append((question, module))
            final_questions.extend(module_questions)
        
        paper.questions = final_questions
        paper.question_module_mapping = new_mapping
        paper.save()
        
        if question_bank and question_bank.question_file:
            available_questions_by_module = {module: [] for module in modules}
            pdf_reader = PdfReader(question_bank.question_file.path)
            current_module = None
            current_question = ""
            
            for page in pdf_reader.pages:
                text = page.extract_text()
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                for line in lines:
                    module_match = re.search(r"(?i)^MODULE\s*[-]?\s*(\d+)\s*:?", line)
                    if module_match:
                        if current_question and current_module in available_questions_by_module:
                            available_questions_by_module[current_module].append(current_question.strip())
                        current_question = ""
                        module_num = module_match.group(1)
                        current_module = f"MODULE-{module_num}"
                        continue
                    
                    if current_module in available_questions_by_module:
                        if line[0].isdigit() and "." in line[:3]:
                            if current_question:
                                available_questions_by_module[current_module].append(current_question.strip())
                            current_question = line.split(".", 1)[1].strip()
                        elif current_question:
                            current_question += " " + line
            
            if current_question and current_module in available_questions_by_module:
                available_questions_by_module[current_module].append(current_question.strip())
            
            for module in available_questions_by_module:
                available_questions_by_module[module] = [
                    q.strip() for q in available_questions_by_module[module] if q and len(q.strip()) > 5
                ]
                for question, orig_module in question_module_mapping:
                    if question in removed_questions and orig_module == module:
                        if question not in available_questions_by_module[module]:
                            available_questions_by_module[module].append(question)
        
        messages.success(request, 'Question paper updated successfully.')
        return redirect('view_question_paper', paper_id=paper.id)
    
    questions_flat = paper.questions
    available_questions_by_module = {module: [] for module in modules}
    if question_bank and question_bank.question_file:
        try:
            pdf_reader = PdfReader(question_bank.question_file.path)
            current_module = None
            current_question = ""
            
            for page in pdf_reader.pages:
                text = page.extract_text()
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                for line in lines:
                    module_match = re.search(r"(?i)^MODULE\s*[-]?\s*(\d+)\s*:?", line)
                    if module_match:
                        if current_question and current_module in available_questions_by_module:
                            available_questions_by_module[current_module].append(current_question.strip())
                        current_question = ""
                        module_num = module_match.group(1)
                        current_module = f"MODULE-{module_num}"
                        continue
                    
                    if current_module in available_questions_by_module:
                        if line[0].isdigit() and "." in line[:3]:
                            if current_question:
                                available_questions_by_module[current_module].append(current_question.strip())
                            current_question = line.split(".", 1)[1].strip()
                        elif current_question:
                            current_question += " " + line
            
            if current_question and current_module in available_questions_by_module:
                available_questions_by_module[current_module].append(current_question.strip())
            
            for module in available_questions_by_module:
                available_questions_by_module[module] = [
                    q.strip() for q in available_questions_by_module[module] if q and len(q.strip()) > 5
                ]
                available_questions_by_module[module] = [
                    q for q in available_questions_by_module[module] if q not in questions_flat
                ]
        
        except Exception as e:
            messages.error(request, f"Error reading question bank: {str(e)}")
    
    context = {
        'paper': paper,
        'questions_per_module': questions_per_module,
        'available_questions_by_module': available_questions_by_module,
        'current_questions': set(questions_flat)
    }
    return render(request, 'edit_question_paper.html', context)

# Export question paper as PDF
@login_required
def export_pdf(request, paper_id):
    paper = get_object_or_404(QuestionPaper, id=paper_id)
    modules = paper.module.split(',')
    
    if hasattr(paper, 'question_module_mapping') and paper.question_module_mapping:
        question_module_mapping = paper.question_module_mapping
    else:
        questions_flat = paper.questions.copy()
        question_module_mapping = []
        questions_per_module = len(questions_flat) // len(modules)
        for i, module in enumerate(modules):
            start_idx = i * questions_per_module
            end_idx = (i + 1) * questions_per_module if i < len(modules) - 1 else len(questions_flat)
            for j in range(start_idx, end_idx):
                if j < len(questions_flat):
                    question_module_mapping.append((questions_flat[j], module))
    
    questions_per_module_dict = {module: [] for module in modules}
    for question, module in question_module_mapping:
        if module in questions_per_module_dict:
            questions_per_module_dict[module].append(question)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{paper.title}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    y = height - inch

    p.setFont("Helvetica-Bold", 16)
    p.drawString(inch, y, paper.title)
    y -= 0.5 * inch

    p.setFont("Helvetica", 12)
    p.drawString(inch, y, f"Module: {paper.module}")
    y -= 0.3 * inch
    p.drawString(inch, y, f"Created By: {paper.created_by}")
    y -= 0.3 * inch
    p.drawString(inch, y, f"Created At: {paper.created_at.strftime('%d %b %Y, %H:%M')}")
    y -= 0.3 * inch
    p.drawString(inch, y, f"Status: {paper.status.title()}")
    y -= 0.5 * inch

    for module, questions in questions_per_module_dict.items():
        p.setFont("Helvetica-Bold", 14)
        p.drawString(inch, y, f"{module} Questions ({len(questions)}):")
        y -= 0.3 * inch

        if not questions:
            p.setFont("Helvetica-Oblique", 12)
            p.drawString(inch, y, "No questions assigned to this module.")
            y -= 0.5 * inch
            continue

        p.setFont("Helvetica", 12)
        for i, question in enumerate(questions, 1):
            if y < inch:
                p.showPage()
                y = height - inch
                p.setFont("Helvetica", 12)
            
            lines = question.split('\n')
            p.drawString(inch, y, f"{i}. {lines[0]}")
            y -= 0.2 * inch
            for line in lines[1:]:
                if y < inch:
                    p.showPage()
                    y = height - inch
                    p.setFont("Helvetica", 12)
                p.drawString(inch + 0.2 * inch, y, line)
                y -= 0.2 * inch
            y -= 0.2 * inch

        y -= 0.5 * inch

    p.showPage()
    p.save()
    return response