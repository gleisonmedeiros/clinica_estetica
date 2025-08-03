from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Agenda, Cliente, Painel
from .forms import AgendaForm, PainelFiltroForm
from django.views.decorators.http import require_http_methods
from datetime import date


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

            # Cria automaticamente o Painel vinculado à Agenda
            Painel.objects.get_or_create(agenda=agenda)

            return redirect('cadastro_agenda')
    else:
        form = AgendaForm()
    return render(request, 'agenda.html', {'form': form})


def autocomplete_cliente(request):
    term = request.GET.get('term', '')
    clientes = Cliente.objects.filter(nome__istartswith=term)[:10]
    results = [{'label': cliente.nome, 'value': cliente.nome, 'telefone': cliente.telefone} for cliente in clientes]
    return JsonResponse(results, safe=False)


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

    agendas = Agenda.objects.filter(data=data_selecionada).order_by('horario')

    agendas_info = []
    for agenda in agendas:
        painel = Painel.objects.filter(agenda=agenda).first()
        agendas_info.append({
            'id': agenda.id,
            'nome': agenda.cliente.nome if getattr(agenda, 'cliente', None) else agenda.nome,
            'telefone': agenda.cliente.telefone if getattr(agenda, 'cliente', None) else agenda.telefone,
            'data': agenda.data.strftime('%d/%m/%Y'),
            'horario': agenda.horario.strftime('%H:%M'),
            'tipo_pacote': agenda.tipo_pacote,
            'quantidade_pacote': agenda.quantidade_pacote,
            'forma_pagamento': agenda.forma_pagamento,
            'valor': agenda.valor,
            'presenca': painel.presenca if painel else False,
        })

    if request.method == "POST":
        # Pega a data do formulário
        data_str = request.POST.get('data')
        print(data_str)
        try:
            data_painel = date.fromisoformat(data_str) if data_str else date.today()
        except ValueError:
            data_painel = date.today()

        print(data_painel)


        for agenda_info in agendas_info:
            presenca_field = f"presenca_{agenda_info['id']}"
            presenca_valor = presenca_field in request.POST

            painel, created = Painel.objects.get_or_create(agenda_id=agenda_info['id'])
            painel.presenca = presenca_valor
            # Se o modelo Painel tivesse campo 'data', salvaríamos aqui, mas não tem:
            # painel.data = data_painel

            painel.save()

        return redirect(f"{request.path}?data={data_painel.strftime('%Y-%m-%d')}")

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

            # Garante que o Painel exista após editar
            Painel.objects.get_or_create(agenda=agenda)

            return redirect('painel_presenca')
    else:
        form = AgendaForm(instance=agenda)
    return render(request, 'agenda.html', {'form': form})


def relatorio_presenca(request):
    data_selecionada = request.GET.get('data')
    if data_selecionada:
        data_obj = date.fromisoformat(data_selecionada)
    else:
        data_obj = date.today()

    agendas = Agenda.objects.filter(data=data_obj)
    painels = Painel.objects.filter(agenda__in=agendas)

    presentes = painels.filter(presenca=True)
    faltantes = painels.filter(presenca=False)

    total_presentes = presentes.count()
    total_faltantes = faltantes.count()
    lucro_total = sum(p.agenda.valor for p in presentes if p.agenda.valor)

    nomes_presentes = [p.agenda.nome for p in presentes]
    nomes_faltantes = [p.agenda.nome for p in faltantes]

    contexto = {
        'data_selecionada': data_obj,
        'total_presentes': total_presentes,
        'total_faltantes': total_faltantes,
        'lucro_total': lucro_total,
        'nomes_presentes': nomes_presentes,
        'nomes_faltantes': nomes_faltantes,
    }

    return render(request, 'relatorio_presenca.html', contexto)
