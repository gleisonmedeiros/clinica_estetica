from django.db import models

class Cliente(models.Model):
    nome = models.CharField(max_length=100)
    telefone = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return f"{self.nome} ({self.telefone})"


class Agenda(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)       # digitado no form
    telefone = models.CharField(max_length=20)    # digitado no form
    data = models.DateField()
    horario = models.TimeField()
    tipo_pacote = models.CharField(max_length=50)
    quantidade_pacote = models.PositiveIntegerField()
    quantidade_pacote_restante = models.PositiveIntegerField()
    forma_pagamento = models.CharField(max_length=30)
    valor = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.nome} - {self.data} {self.horario}"

class Painel(models.Model):
    agenda = models.ForeignKey(Agenda, on_delete=models.CASCADE)
    presenca = models.BooleanField(default=False, help_text="Marque se o cliente compareceu")

    def __str__(self):
        status = "Compareceu" if self.presenca else "Faltou"
        return f"Painel: {self.agenda} - {status}"