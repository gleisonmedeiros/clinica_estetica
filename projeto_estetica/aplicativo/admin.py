from django.contrib import admin
from .models import Cliente, Agenda, Painel

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'telefone')
    search_fields = ('nome', 'telefone')

@admin.register(Agenda)
class AgendaAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'data', 'horario', 'tipo_pacote', 'forma_pagamento', 'valor')
    list_filter = ('data', 'tipo_pacote', 'forma_pagamento')
    search_fields = ('cliente__nome',)  # 'telefone' removido pois não existe maiss

@admin.register(Painel)
class PainelAdmin(admin.ModelAdmin):
    list_display = ('agenda', 'presenca')
    list_filter = ('presenca',)
