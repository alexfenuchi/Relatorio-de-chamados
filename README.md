# Relatório de Chamados — Suporte N2

Aplicação em Streamlit para análise da base anual de chamados do Suporte N2.

## Funcionalidades

- Upload de Excel anual
- Tratamento automático de datas do Excel
- Remoção de duplicidades por número de chamado
- Indicadores de chamados encerrados, pendentes e SLA
- Evolução semanal
- Top problemas
- Top lojas
- Análise por responsável
- Filtros por período, loja, problema, status, responsável e SLA
- Exportação do relatório filtrado em Excel

## Estrutura esperada da base

A aplicação foi preparada para a base `base_chamados_2026.xlsx`, com colunas como:

- N° Chamado
- Título
- prioridade
- Tipo do Chamado
- TipoLocalizacao
- Localizacao
- Abertura
- Situacao
- StatusSLA
- Equipe Responsavel
- Responsavel
- Categoria
- Produto
- Problema
- Encerramento
- descricao
- solucao
- Código de solução

## Instalação local

```powershell
cd "C:\Projetos\Relatorio de chamados"

py -m venv .venv

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

.\.venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt

python -m streamlit run app.py
```

## GitHub

```powershell
git init
git add .
git commit -m "Dashboard completo de chamados N2"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/relatorio-chamados-n2.git
git push -u origin main
```

## Observação de segurança

A base Excel está bloqueada no `.gitignore` e não deve ser enviada ao GitHub.
