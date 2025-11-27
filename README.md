# 🏥 Clinica Estetica

Sistema de agendamento para clínica de estética desenvolvido em **Django**, com controle de clientes, agendamentos, presenças e geração de relatórios em PDF.

---

## 🚀 Funcionalidades

- Cadastro de clientes e agendamentos
- Marcação de presença
- Autocomplete de clientes
- Edição e exclusão de agendas
- Relatórios financeiros e de presença
- Geração de PDF com a lista do dia

---

## 🛠 Tecnologias

- **Python 3.x**
- **Django 4.x**
- **ReportLab** (para PDFs)

---

## ⚡ Instalação

1. Clone o repositório:

```bash
git clone https://github.com/gleisonmedeiros/clinica_estetica
cd clinica-estetica
Crie e ative o ambiente virtual:

bash
Copiar código
python -m venv venv
source venv/bin/activate  # Linux/macOS
# Windows
venv\Scripts\activate
Instale as dependências:

bash
Copiar código
pip install -r requirements.txt
Execute as migrações:

bash
Copiar código
python manage.py migrate
Crie um superusuário:

bash
Copiar código
python manage.py createsuperuser
Inicie o servidor:

bash
Copiar código
python manage.py runserver
Abra no navegador:

cpp
Copiar código
http://127.0.0.1:8000
📁 Estrutura do Projeto
cpp
Copiar código
clinica_estetica/
├── manage.py
├── clinica_estetica/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── app/
    ├── models.py
    ├── views.py
    ├── forms.py
    ├── templates/
    └── static/
📄 Licença
Este projeto está licenciado sob a MIT License. Consulte o arquivo LICENSE para mais detalhes.