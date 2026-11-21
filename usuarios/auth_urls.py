"""Compatibilidade com as URLs de autenticação do DRF, usando o login comum."""
from allauth.account.views import LoginView
from django.contrib.auth.views import LogoutView
from django.urls import path

app_name = 'rest_framework'

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
