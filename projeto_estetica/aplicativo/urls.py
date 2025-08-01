from django.urls import path
from . import views

urlpatterns = [
    path('painel-presenca/', views.painel_presenca, name='painel_presenca'),
    path('agenda/editar/<int:pk>/', views.editar_agenda, name='editar_agenda'),
    path('autocomplete-cliente/', views.autocomplete_cliente, name='autocomplete_cliente'),
    path('cadastro-agenda/', views.cadastro_agenda, name='cadastro_agenda'),
]