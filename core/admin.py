from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, QuestionBank, QuestionPaper

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'email')
    ordering = ('-id',)  # Use 'id' since 'date_joined' doesn't exist
    
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal info', {'fields': ('role',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_admin')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'role'),
        }),
    )
    
    # Override filter_horizontal to remove references to 'groups' and 'user_permissions'
    filter_horizontal = ()

class QuestionBankAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'created_by', 'created_at')
    list_filter = ('module', 'created_at', 'created_by')
    search_fields = ('title', 'module')
    ordering = ('-created_at',)

class QuestionPaperAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'created_by', 'created_at', 'status')
    list_filter = ('module', 'status', 'created_at', 'created_by')
    search_fields = ('title', 'module')
    ordering = ('-created_at',)

admin.site.register(User, CustomUserAdmin)
admin.site.register(QuestionBank, QuestionBankAdmin)
admin.site.register(QuestionPaper, QuestionPaperAdmin)