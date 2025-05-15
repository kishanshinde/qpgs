from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

class UserManager(BaseUserManager):
    def create_user(self, email, username, password=None):
        if not email:
            raise ValueError("Users must have an email address")
        if not username:
            raise ValueError("Users must have a username")

        user = self.model(
            email=self.normalize_email(email),
            username=username,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None):
        user = self.create_user(
            email,
            username,
            password=password,
        )
        user.is_admin = True
        user.is_staff = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser):
    email = models.EmailField(verbose_name="email address", max_length=255, unique=True)
    username = models.CharField(max_length=150, unique=True)
    role = models.CharField(
        max_length=20,
        choices=[('teacher', 'Teacher'), ('exam', 'Exam'), ('admin', 'Admin')],
        default='teacher'
    )
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True, blank=True)  # Add last_login field

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

class QuestionBank(models.Model):
    title = models.CharField(max_length=255)
    module = models.CharField(max_length=255)
    question_file = models.FileField(upload_to='question_banks/')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class QuestionPaper(models.Model):
    title = models.CharField(max_length=255)
    module = models.CharField(max_length=255)
    questions = models.JSONField(default=list)
    question_module_mapping = models.JSONField(default=list)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    question_bank = models.ForeignKey(QuestionBank, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('draft', 'Draft'), ('final', 'Final')], default='draft')

    def __str__(self):
        return self.title