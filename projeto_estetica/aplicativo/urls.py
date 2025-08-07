from django.urls import path
from . import views

urlpatterns = [
    path('painel-presenca/', views.painel_presenca, name='painel_presenca'),
    path('agenda/editar/<int:pk>/', views.editar_agenda, name='editar_agenda'),
    path('autocomplete-cliente/', views.autocomplete_cliente, name='autocomplete_cliente'),
    path('cadastro-agenda/', views.cadastro_agenda, name='cadastro_agenda'),
    path('relatorio-presenca/', views.relatorio_presenca, name='relatorio_presenca'),
    path('painel/exportar-pdf/', views.exportar_pdf, name='exportar_pdf'),
]