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
import traceback
from io import BytesIO
import time

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
    print("Iniciando exportar_pdf")

    data_str = request.GET.get('data')
    print(f"Parâmetro data recebido: {data_str}")

    try:
        data_selecionada = date.fromisoformat(data_str) if data_str else date.today()
        print(f"Data convertida: {data_selecionada}")
    except ValueError:
        print("Erro ao converter data, usando data atual")
        data_selecionada = date.today()

    try:
        print("Consultando banco de dados...")
        agendas = list(Agenda.objects.filter(data=data_selecionada).select_related('cliente'))
        print(f"Foram encontrados {len(agendas)} agendas para a data {data_selecionada}")
    except Exception as e:
        print(f"Erro ao consultar banco: {e}")
        raise

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))

    titulo_style = ParagraphStyle(
        name="Titulo",
        fontSize=16,
        leading=20,
        alignment=1,  # centro
        spaceAfter=1 * cm
    )

    data = [[
        "Nome", "Telefone", "Data", "Horário", "Tipo", "Qtde", "Área", "Forma Pagamento", "Valor"
    ]]

    for agenda in agendas:
        try:
            linha = [
                agenda.cliente.nome if agenda.cliente else "",
                agenda.cliente.telefone if agenda.cliente else "",
                agenda.data.strftime('%d/%m/%Y'),
                agenda.horario.strftime('%H:%M') if agenda.horario else "",
                agenda.tipo_pacote or "",
                agenda.quantidade_pacote or "",
                agenda.cliente.area if agenda.cliente else "",
                agenda.forma_pagamento or "",
                f"R$ {agenda.valor:.2f}" if agenda.valor is not None else ""
            ]
            print(f"Adicionando linha: {linha}")
            data.append(linha)
        except Exception as e:
            print(f"Erro nos dados da agenda id={agenda.id}: {e}")

    tabela = Table(data, repeatRows=1)
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")])
    ]))

    elementos = []
    elementos.append(Paragraph(f"Clientes do dia - {data_selecionada.strftime('%d/%m/%Y')}", titulo_style))
    elementos.append(Spacer(1, 12))
    elementos.append(tabela)

    try:
        print("Gerando PDF...")
        doc.build(elementos)
        print("PDF gerado com sucesso!")
    except Exception as e:
        print("Erro ao gerar PDF:")
        import traceback
        traceback.print_exc()
        raise

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="clientes_{data_selecionada}.pdf"'
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
