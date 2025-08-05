from django.db import models

class Cliente(models.Model):
    nome = models.CharField(max_length=100)
    telefone = models.CharField(max_length=20)
    area = models.CharField(max_length=100,default='Geral')

    def __str__(self):
        return f"{self.nome} ({self.telefone} {self.area})"


class Agenda(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    data = models.DateField()
    horario = models.TimeField()

    # Campos opcionais
    tipo_pacote = models.CharField(max_length=30, blank=True, null=True)
    quantidade_pacote = models.CharField(max_length=30, blank=True, null=True)
    forma_pagamento = models.CharField(max_length=30, blank=True, null=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"{self.cliente.nome} - {self.data} {self.horario}"

class Painel(models.Model):
    agenda = models.OneToOneField(Agenda, on_delete=models.CASCADE)
    presenca = models.BooleanField(default=False, help_text="Marque se o cliente compareceu")

    def __str__(self):
        status = "Compareceu" if self.presenca else "Faltou"
        return f"Painel: {self.agenda} - {status}"