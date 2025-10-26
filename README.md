# 🔧📦 MTDL-PCM - Sistema de Manutenção e Controle de Equipamentos

Sistema web completo para gestão de manutenção e controle de equipamentos, desenvolvido em Python com FastAPI.

## 📋 Visão Geral

O MTDL-PCM é uma aplicação web moderna que oferece controle completo sobre:

- **Manutenção de Equipamentos**: Ordens de serviço, planos preventivos, controle de horímetro
- **Gestão de Almoxarifado**: Controle de estoque, requisições, cotações e fornecedores
- **Relatórios e KPIs**: MTTR, MTBF, análise ABC, performance de fornecedores
- **Dashboard Interativo**: Métricas em tempo real e alertas automáticos

## 🚀 Tecnologias Utilizadas

### Backend
- **FastAPI**: Framework web moderno e rápido
- **SQLAlchemy**: ORM para banco de dados
- **SQLite**: Banco de dados (com possibilidade de migração para PostgreSQL)
- **Pydantic**: Validação de dados
- **Uvicorn**: Servidor ASGI

### Frontend
- **HTML5 + CSS3 + JavaScript**: Interface responsiva
- **Bootstrap 5**: Framework CSS
- **Chart.js**: Gráficos interativos
- **Axios**: Cliente HTTP para APIs

## 📁 Estrutura do Projeto

```
MTDL PCM/
├── app/
│   ├── __init__.py
│   ├── database.py              # Configuração do banco de dados
│   ├── models/                  # Modelos SQLAlchemy
│   │   ├── __init__.py
│   │   ├── equipment.py         # Equipamentos e horímetro
│   │   ├── maintenance.py       # Manutenção e ordens de serviço
│   │   └── warehouse.py         # Almoxarifado e estoque
│   ├── routers/                 # Endpoints da API
│   │   ├── __init__.py
│   │   ├── dashboard.py         # Dashboard e métricas
│   │   ├── maintenance.py       # Módulo de manutenção
│   │   ├── warehouse.py         # Módulo de almoxarifado
│   │   └── reports.py           # Relatórios e KPIs
│   └── schemas/                 # Schemas Pydantic
│       ├── __init__.py
│       └── maintenance.py       # Validação de dados
├── templates/                   # Templates HTML
│   ├── base.html               # Template base
│   ├── index.html              # Dashboard principal
│   ├── error.html              # Páginas de erro
│   ├── maintenance/
│   │   └── work_orders.html    # Ordens de serviço
│   └── warehouse/
│       └── materials.html      # Gestão de materiais
├── static/                     # Arquivos estáticos
│   ├── css/
│   │   └── style.css          # Estilos personalizados
│   └── js/
│       └── app.js             # JavaScript principal
├── data/                       # Banco de dados SQLite
├── main.py                     # Aplicação principal
├── requirements.txt            # Dependências Python
└── README.md                   # Este arquivo
```

## 🛠️ Instalação e Configuração

### Pré-requisitos
- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

### Passo a Passo

1. **Clone ou baixe o projeto**
   ```bash
   cd "MTDL PCM"
   ```

2. **Crie um ambiente virtual (recomendado)**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Instale as dependências**
   ```bash
   pip install -r requirements.txt
   ```

4. **Execute a aplicação**
   ```bash
   python main.py
   ```

5. **Acesse o sistema**
   - **Interface Web**: http://localhost:8000
   - **Documentação da API**: http://localhost:8000/docs
   - **Redoc**: http://localhost:8000/redoc

## 📊 Funcionalidades Principais

### 🔧 Módulo Manutenção

#### Dashboard Manutenção
- Métricas em tempo real (OS abertas, em andamento, equipamentos em manutenção)
- Alertas de manutenção preventiva
- Tempo médio de resolução (MTTR)

#### Ordens de Serviço
- Numeração automática (início: 100000)
- Status: Aberta / Em andamento / Fechada
- Vinculação com equipamentos
- Controle de materiais aplicados
- Registro de homem-hora

#### Equipamentos
- Cadastro completo (prefixo, modelo, fabricante, ano)
- Controle de horímetro com validação
- Status operacional
- Histórico de manutenções

#### Planos de Manutenção
- Preventiva, corretiva, preditiva
- Intervalos por tempo ou uso
- Checklists personalizados
- Geração automática de OS

### 📦 Módulo Almoxarifado

#### Gestão de Estoque
- Cadastro completo de materiais
- Controle de entradas e saídas
- Inventário em tempo real
- Localização física

#### Requisições de Compra
- Solicitação por setor
- Justificativa e especificações
- Controle de aprovações

#### Fornecedores e Cotações
- Cadastro de fornecedores
- Comparativo de preços
- Histórico de compras

### 📈 Relatórios e KPIs

- **MTTR/MTBF**: Tempo médio entre falhas e reparo
- **Custos por Equipamento**: Análise de gastos
- **Produtividade**: Performance de técnicos
- **Análise ABC**: Classificação de materiais
- **Giro de Estoque**: Rotatividade de materiais
- **Performance de Fornecedores**: Avaliação de parceiros

## 🔒 Segurança

- Validação de dados com Pydantic
- Tratamento de exceções
- Logs de auditoria
- Preparado para autenticação JWT (implementação futura)

## 🧪 Testes

Execute os testes automatizados:

```bash
pytest
```

## 📝 Desenvolvimento

### Estrutura de Desenvolvimento
- **Linting**: flake8, black, isort
- **Testes**: pytest, pytest-asyncio
- **Documentação**: Swagger automático via FastAPI

### Adicionando Novas Funcionalidades

1. **Modelos**: Adicione em `app/models/`
2. **Schemas**: Defina validações em `app/schemas/`
3. **Routers**: Implemente endpoints em `app/routers/`
4. **Templates**: Crie interfaces em `templates/`

## 🚀 Deploy

### Desenvolvimento Local
```bash
python main.py
```

### Produção
Para deploy em produção, considere:

- **Gunicorn**: Servidor WSGI para produção
- **PostgreSQL**: Banco de dados robusto
- **Docker**: Containerização
- **Nginx**: Proxy reverso

Exemplo com Gunicorn:
```bash
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## 📞 Suporte

Para dúvidas, sugestões ou problemas:

1. Verifique a documentação da API em `/docs`
2. Consulte os logs da aplicação
3. Abra uma issue no repositório

## 📄 Licença

Este projeto está sob licença MIT. Veja o arquivo LICENSE para mais detalhes.

## 🔄 Roadmap

### Próximas Funcionalidades
- [ ] Autenticação e autorização (RBAC)
- [ ] Integração com ERP via API
- [ ] Conectividade IoT
- [ ] App mobile
- [ ] Dashboards avançados com Plotly/Dash
- [ ] Backup automático
- [ ] Notificações por email/SMS

---

**MTDL-PCM** - Desenvolvido com ❤️ em Python