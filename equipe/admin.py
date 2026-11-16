from django.contrib import admin

from .models import Aluno, Curso, Professor

admin.site.register(Aluno)
admin.site.register(Professor)
admin.site.register(Curso)
