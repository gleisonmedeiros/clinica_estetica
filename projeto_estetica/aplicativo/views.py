from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Agenda, Cliente, Painel
from .forms import AgendaForm, PainelFiltroForm
from django.views.decorators.http import require_http_methods

def cadastro_agenda(request):
    if request.method == "POST":
        form = AgendaForm(request.POST)
        if form.is_valid():
            agenda = form.save(commit=False)
            cliente, created = Cliente.objects.get_or_create(
                telefone=agenda.telefone,
                defaults={'nome': agenda.nome}
            )
            agenda.cliente = cliente
            agenda.save()
            return redirect('cadastro_agenda')
    else:
        form = AgendaForm()
    return render(request, 'agenda.html', {'form': form})

def autocomplete_cliente(request):
    term = request.GET.get('term', '')
    clientes = Cliente.objects.filter(nome__istartswith=term).values_list('nome', flat=True)[:10]
    results = list(clientes)
    return JsonResponse(results, safe=False)

TIPO_PACOTE_DICT = {
    'avulso': 'Avulso',
    'pacote': 'Pacote',
    'parceria': 'Parceria',
}

FORMA_PAGAMENTO_DICT = {
    'pix': 'Pix',
    'dinheiro': 'Dinheiro',
    'cartao': 'Cartão',
}


from datetime import date

@require_http_methods(["GET", "POST"])
def painel_presenca(request):
    if request.method == "GET":
        filtro_form = PainelFiltroForm(request.GET or None)
    else:
        filtro_form = PainelFiltroForm(request.POST or None)

    if filtro_form.is_valid() and filtro_form.cleaned_data['data']:
        data_selecionada = filtro_form.cleaned_data['data']
    else:
        data_selecionada = date.today()

    # Filtra agendas pela data selecionada (que agora nunca será None)
    agendas = Agenda.objects.filter(data=data_selecionada).order_by('horario')

    agendas_info = []
    for agenda in agendas:
        painel = Painel.objects.filter(agenda=agenda).first()
        agendas_info.append({
            'id': agenda.id,
            'nome': agenda.cliente.nome if hasattr(agenda, 'cliente') else agenda.nome,
            'telefone': agenda.cliente.telefone if hasattr(agenda, 'cliente') else agenda.telefone,
            'data': agenda.data.strftime('%d/%m/%Y'),
            'horario': agenda.horario.strftime('%H:%M'),
            'tipo_pacote': agenda.tipo_pacote,
            'quantidade_pacote': agenda.quantidade_pacote,
            'quantidade_pacote_restante': agenda.quantidade_pacote_restante,
            'forma_pagamento': agenda.forma_pagamento,
            'valor': agenda.valor,
            'presenca': painel.presenca if painel else False,
        })

    if request.method == "POST":
        for agenda_info in agendas_info:
            presenca_field = f"presenca_{agenda_info['id']}"
            presenca_valor = presenca_field in request.POST

            painel, created = Painel.objects.get_or_create(agenda_id=agenda_info['id'])
            painel.presenca = presenca_valor
            painel.save()

        return redirect(f"{request.path}?data={data_selecionada.strftime('%Y-%m-%d')}")

    return render(request, 'painel.html', {
        'form': filtro_form,
        'agendas_info': agendas_info,
        'data_selecionada': data_selecionada,
    })


def editar_agenda(request, pk):
    agenda = get_object_or_404(Agenda, pk=pk)
    if request.method == 'POST':
        form = AgendaForm(request.POST, instance=agenda)
        if form.is_valid():
            form.save()
            return redirect('painel_presenca')
    else:
        form = AgendaForm(instance=agenda)
    return render(request, 'agenda.html', {'form': form})