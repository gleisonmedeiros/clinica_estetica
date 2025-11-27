from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Agenda, Cliente, Painel,ClienteLink
from .forms import AgendaForm, PainelFiltroForm, ClienteForm

import time
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from datetime import date
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm


import uuid
from django.utils.text import slugify


def cadastro_agenda(request):
    copiado = request.session.pop('agenda_copiada', None)
    if copiado:
        form = AgendaForm(initial=copiado)
    else:
        form = AgendaForm()

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
    return render(request, 'agenda.html', {'form': form})


def autocomplete_cliente(request):
    term = request.GET.get('term', '')
    clientes = Cliente.objects.filter(nome__istartswith=term)[:10]
    results = [{'label': c.nome, 'value': c.nome, 'telefone': c.telefone, 'area':c.area} for c in clientes]
    return JsonResponse(results, safe=False)


@require_http_methods(["GET", "POST"])
def painel_presenca(request):
    filtro_form = PainelFiltroForm(request.GET if request.method == "GET" else request.POST)

    data_selecionada = (
        filtro_form.cleaned_data['data']
        if filtro_form.is_valid() and filtro_form.cleaned_data.get('data')
        else date.today()
    )

    # Pré-carrega cliente e painel para evitar N+1 queries
    agendas = (
        Agenda.objects
        .filter(data=data_selecionada)
        .select_related('cliente')
        .order_by('horario')
    )
    paineis = {p.agenda_id: p for p in Painel.objects.filter(agenda__in=agendas)}

    agendas_info = []
    for agenda in agendas:
        painel = paineis.get(agenda.id)
        cliente = agenda.cliente
        agendas_info.append({
            'id': agenda.id,
            'nome': cliente.nome,
            'telefone': cliente.telefone,
            'area': cliente.area,
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
        except (ValueError, TypeError):
            data_painel = date.today()

        # Atualiza todos os painéis em lote
        painel_updates = []
        for agenda_info in agendas_info:
            presenca_field = f"presenca_{agenda_info['id']}"
            presenca_valor = presenca_field in request.POST

            painel = paineis.get(agenda_info['id'])
            if painel and painel.presenca != presenca_valor:
                painel.presenca = presenca_valor
                painel_updates.append(painel)

        if painel_updates:
            Painel.objects.bulk_update(painel_updates, ['presenca'])

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

    print("Iniciando consulta no banco de dados...")
    start_time = time.time()  # tempo início

    try:
        agendas = list(Agenda.objects.filter(data=data_selecionada).select_related('cliente').order_by('horario'))
    except Exception as e:
        print(f"Erro ao consultar banco: {e}")
        raise

    elapsed_time = time.time() - start_time  # tempo fim - início
    print(f"Consulta finalizada. Tempo gasto: {elapsed_time:.4f} segundos")
    print(f"Foram encontrados {len(agendas)} agendas para a data {data_selecionada}")

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
            #print(f"Adicionando linha: {linha}")
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

        if 'copy_agenda' in request.POST:
            request.session['agenda_copiada'] = {
                'nome': agenda.cliente.nome,
                'telefone': agenda.cliente.telefone,
                'area': agenda.cliente.area,
                'horario': str(agenda.horario),
                'tipo_pacote': agenda.tipo_pacote,
                'quantidade_pacote': agenda.quantidade_pacote,
                'forma_pagamento': agenda.forma_pagamento,
                'valor': str(agenda.valor),
                # 'data' propositalmente omitido
            }
            return redirect('cadastro_agenda')

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
    data_str = request.GET.get('data')
    try:
        data_obj = date.fromisoformat(data_str) if data_str else date.today()
    except (ValueError, TypeError):
        data_obj = date.today()

    # Carrega agendas com cliente e painel em uma única consulta
    agendas = (
        Agenda.objects
        .filter(data=data_obj)
        .select_related('cliente')
    )
    paineis = (
        Painel.objects
        .filter(agenda__in=agendas)
        .select_related('agenda__cliente')
    )

    # Pré-processa os dados
    total_presentes = total_faltantes = lucro_total = 0
    nomes_presentes = []
    nomes_faltantes = []

    for painel in paineis:
        cliente_nome = painel.agenda.cliente.nome
        valor = painel.agenda.valor or 0

        if painel.presenca:
            total_presentes += 1
            lucro_total += valor
            nomes_presentes.append(cliente_nome)
        else:
            total_faltantes += 1
            nomes_faltantes.append(cliente_nome)

    contexto = {
        'data_selecionada': data_obj,
        'total_presentes': total_presentes,
        'total_faltantes': total_faltantes,
        'lucro_total': lucro_total,
        'nomes_presentes': nomes_presentes,
        'nomes_faltantes': nomes_faltantes,
    }

    return render(request, 'relatorio_presenca.html', contexto)

def gerar_codigo():
    return uuid.uuid4().hex[:10]

def asscontrato(request):
    links = ClienteLink.objects.all()
    form = ClienteForm(request.GET or None)
    cliente_selecionado = None
    link_gerado = None
    link_completo = None  # <--- adicionar

    if form.is_valid():
        cliente_id = form.cleaned_data['nome']
        cliente = Cliente.objects.get(id=cliente_id)
        cliente_selecionado = cliente.nome

        # ==== Criação do link único ====
        codigo = gerar_codigo()
        nome_slug = slugify(cliente.nome)

        # URL relativa
        url = f"/cliente/{nome_slug}/{codigo}/"

        # URL completa (funciona no DEV e PRODUÇÃO)
        link_completo = request.build_absolute_uri(url)

        # Salva no banco
        ClienteLink.objects.create(
            cliente=cliente,
            codigo=codigo,
            link_completo=link_completo  # <--- salvar COMPLETA agora
        )

        link_gerado = url

    context = {
        "form": form,
        "cliente_selecionado": cliente_selecionado,
        "link_gerado": link_gerado,
        "link_completo": link_completo,  # <---
        "links": links,
    }
    return render(request, 'contrato.html', context)


def excluir_link(request, pk):
    link = get_object_or_404(ClienteLink, pk=pk)
    link.delete()
    return redirect("asscontrato")  # voltar para a página principal

def mensagem_view(request, nome, codigo):

    try:
        link = ClienteLink.objects.get(codigo=codigo)
        cliente = link.cliente
    except ClienteLink.DoesNotExist:
        return HttpResponse("Link inválido!")

    return render(request, "assinatura.html", {"cliente": cliente})

