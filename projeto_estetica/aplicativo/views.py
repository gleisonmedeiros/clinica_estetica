from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Agenda, Cliente, Painel
from .forms import AgendaForm, PainelFiltroForm
from django.views.decorators.http import require_http_methods
from datetime import date
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from django.http import HttpResponse
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm


def cadastro_agenda(request):
    if request.method == "POST":
        form = AgendaForm(request.POST)
        if form.is_valid():
            nome = form.cleaned_data['nome']
            telefone = form.cleaned_data['telefone']
            area = form.cleaned_data['area']

            # Buscar cliente por nome (case-insensitive)
            cliente = Cliente.objects.filter(nome__iexact=nome).first()
            if cliente:
                cliente.telefone = telefone
                cliente.area = area
                cliente.save()
            else:
                cliente = Cliente.objects.create(nome=nome, telefone=telefone,area=area)

            agenda = form.save(commit=False)
            agenda.cliente = cliente
            agenda.save()

            Painel.objects.get_or_create(agenda=agenda)

            return redirect('cadastro_agenda')
    else:
        form = AgendaForm()
    return render(request, 'agenda.html', {'form': form})


def autocomplete_cliente(request):
    term = request.GET.get('term', '')
    clientes = Cliente.objects.filter(nome__istartswith=term)[:10]
    results = [{'label': c.nome, 'value': c.nome, 'telefone': c.telefone, 'area':c.area} for c in clientes]
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
            'nome': agenda.cliente.nome if getattr(agenda, 'cliente', None) else '',
            'telefone': agenda.cliente.telefone if getattr(agenda, 'cliente', None) else '',
            'area': agenda.cliente.area if getattr(agenda, 'cliente', None) else '',
            'data': agenda.data.strftime('%d/%m/%Y'),
            'horario': agenda.horario.strftime('%H:%M'),
            'tipo_pacote': agenda.tipo_pacote,
            'quantidade_pacote': agenda.quantidade_pacote,
            'forma_pagamento': agenda.forma_pagamento,
            'valor': agenda.valor,
            'presenca': painel.presenca if painel else False,
        })

    if request.method == "POST":
        data_str = request.POST.get('data')
        try:
            data_painel = date.fromisoformat(data_str) if data_str else date.today()
        except ValueError:
            data_painel = date.today()

        for agenda_info in agendas_info:
            presenca_field = f"presenca_{agenda_info['id']}"
            presenca_valor = presenca_field in request.POST

            painel = Painel.objects.filter(agenda_id=agenda_info['id']).first()
            if painel:
                painel.presenca = presenca_valor
                painel.save()

        return redirect(f"{request.path}?data={data_painel.strftime('%Y-%m-%d')}")

    return render(request, 'painel.html', {
        'form': filtro_form,
        'agendas_info': agendas_info,
        'data_selecionada': data_selecionada,
    })


@require_http_methods(["GET"])
def exportar_pdf(request):
    data_str = request.GET.get('data')
    try:
        data_selecionada = date.fromisoformat(data_str) if data_str else date.today()
    except ValueError:
        data_selecionada = date.today()

    agendas = Agenda.objects.filter(data=data_selecionada).order_by('horario')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Clientes_{data_selecionada}.pdf"'

    buffer = []
    doc = SimpleDocTemplate(response, pagesize=landscape(A4))
    styles = getSampleStyleSheet()

    data = [[
        "Nome", "Telefone", "Data", "Horário", "Tipo", "Qtde", "Área", "Forma Pagamento", "Valor"
    ]]

    for agenda in agendas:
        painel = Painel.objects.filter(agenda=agenda).first()
        data.append([
            agenda.cliente.nome if agenda.cliente else '',
            agenda.cliente.telefone if agenda.cliente else '',
            agenda.data.strftime('%d/%m/%Y'),
            agenda.horario.strftime('%H:%M'),
            agenda.tipo_pacote,
            agenda.quantidade_pacote,
            agenda.cliente.area if agenda.cliente else '',
            agenda.forma_pagamento,
            f"R$ {agenda.valor:.2f}",
        ])

    tabela = Table(data, repeatRows=1)
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")])
    ]))
    # Estilo customizado centralizado
    titulo_style = ParagraphStyle(
        name='TituloCentralizado',
        parent=styles['Heading2'],
        alignment=1,  # 0=left, 1=center, 2=right
        spaceAfter=1 * cm  # Espaço abaixo do título
    )

    # Título centralizado com espaçamento
    buffer.append(Paragraph(f"Clientes do dia - {data_selecionada.strftime('%d/%m/%Y')}", titulo_style))
    buffer.append(tabela)

    # Gera o PDF
    doc.build(buffer)

    return response


def editar_agenda(request, pk):
    agenda = get_object_or_404(Agenda, pk=pk)

    if request.method == 'POST':

        # Verifica se o usuário clicou no botão para deletar agenda (e painel)
        if 'delete_agenda' in request.POST:
            # Apaga o painel associado, se existir
            Painel.objects.filter(agenda=agenda).delete()
            # Apaga a agenda
            agenda.delete()
            return redirect('painel_presenca')

        form = AgendaForm(request.POST, instance=agenda)
        if form.is_valid():
            nome = form.cleaned_data['nome']
            telefone = form.cleaned_data['telefone']
            area = form.cleaned_data['area']

            cliente = agenda.cliente
            cliente.nome = nome
            cliente.telefone = telefone
            cliente.area = area
            cliente.save()

            agenda = form.save(commit=False)
            agenda.cliente = cliente
            agenda.save()

            Painel.objects.get_or_create(agenda=agenda)

            return redirect('painel_presenca')
    else:
        initial = {
            'nome': agenda.cliente.nome,
            'telefone': agenda.cliente.telefone,
            'area': agenda.cliente.area,
        }
        form = AgendaForm(instance=agenda, initial=initial)

    return render(request, 'agenda.html', {'form': form, 'agenda': agenda})


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

    nomes_presentes = [p.agenda.cliente.nome for p in presentes]
    nomes_faltantes = [p.agenda.cliente.nome for p in faltantes]

    contexto = {
        'data_selecionada': data_obj,
        'total_presentes': total_presentes,
        'total_faltantes': total_faltantes,
        'lucro_total': lucro_total,
        'nomes_presentes': nomes_presentes,
        'nomes_faltantes': nomes_faltantes,
    }

    return render(request, 'relatorio_presenca.html', contexto)
