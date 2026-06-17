# Relatório de Chamados — Suporte N2

Dashboard Streamlit conectado ao Supabase para armazenar e analisar a base anual de chamados.

## Funcionalidades

- Área administrativa protegida por senha
- Upload do Excel anual
- Upsert dos chamados pelo número do chamado
- Dashboard consultando o Supabase
- Indicadores, análise semanal, problemas, lojas e responsáveis
- Filtros por período, loja, problema, situação, responsável e SLA
- Exportação do relatório filtrado em Excel
- Remoção automática de milhares de colunas vazias/formatadas do Excel

## Configuração do Supabase

Execute o arquivo `sql/criar_tabelas.sql` no SQL Editor do Supabase.

## Secrets do Streamlit Cloud

Em `Manage app → Settings → Secrets`, configure:

```toml
SUPABASE_URL = "https://SEU-PROJETO.supabase.co"
SUPABASE_KEY = "SUA-CHAVE-SECRETA"
ADMIN_PASSWORD = "SUA-SENHA-DE-ADMIN"
```

## Execução local

```powershell
cd "C:\Projetos\Relatorio de chamados"
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Para execução local, crie `.streamlit/secrets.toml` com as mesmas chaves. Esse arquivo está bloqueado no `.gitignore`.

## Publicação

O arquivo principal no Streamlit Community Cloud deve ser:

```text
streamlit_app.py
```
