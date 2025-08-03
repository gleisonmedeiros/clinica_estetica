from django import forms
from .models import Agenda


class AgendaForm(forms.ModelForm):
    FORMA_PAGAMENTO_CHOICES = [
        ('', ''),
        ('pix', 'Pix'),
        ('dinheiro', 'Dinheiro'),
        ('cartao', 'Cartão'),
    ]

    TIPO_PACOTE_CHOICES = [
        ('', ''),
        ('avulso', 'Avulso'),
        ('pacote', 'Pacote'),
        ('parceria', 'Parceria'),
    ]

    nome = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'id': 'id_nome',
            'class': 'form-control',
            'autocomplete': 'off',  # para evitar autofill do navegador
        }),
        label="Nome"
    )

    quantidade_pacote = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'id': 'id_quantidade_pacote',
            'class': 'form-control',
            'autocomplete': 'off',
        }),
        label="Quantidade do Pacote"
    )

    telefone = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Telefone"
    )
    tipo_pacote = forms.ChoiceField(
        required=False,
        choices=TIPO_PACOTE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Tipo de Pacote"
    )
    forma_pagamento = forms.ChoiceField(
        required=False,
        choices=FORMA_PAGAMENTO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Forma de Pagamento"
    )

    class Meta:
        model = Agenda
        fields = [
            'data', 'horario',
            'tipo_pacote', 'quantidade_pacote',
            'forma_pagamento', 'valor'
        ]
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'horario': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class PainelFiltroForm(forms.Form):
    data = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control',
                'placeholder': 'Selecione a data',
            }
        )
    )