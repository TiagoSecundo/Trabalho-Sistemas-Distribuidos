from django.urls import path
from .api import MinhaContaView

from .api import MinhaContaView, MinhasMonografiasView

urlpatterns = [
    path('me/', MinhaContaView.as_view(), name='me'),
    path('monografias/', MinhasMonografiasView.as_view(), name='minhas-monografias'),
]