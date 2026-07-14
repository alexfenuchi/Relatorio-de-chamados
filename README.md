# Central de Inteligência de Chamados — Suporte N2

Aplicação em Streamlit para análise executiva da base anual de chamados do Suporte N2, com foco em volume, SLA, backlog e ofensores recorrentes.

## Funcionalidades

- Upload de Excel anual
- Tratamento automático de datas do Excel
- Remoção de duplicidades por número de chamado
- Indicadores de chamados encerrados, pendentes e SLA
- Evolução semanal
- Top problemas
- Top localizações
- Análise por responsável
- Filtros por período, grupo, localização, problema, status, responsável e SLA
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

python -m streamlit run streamlit_app.py
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

## Melhorias operacionais recentes

- O KPI principal de SLA agora usa a medição recalculada pelo dashboard, comparando o nível SLA com o tempo útil de resolução ou aging dos chamados pendentes.
- A visão inicial inclui indicadores diários: chamados abertos hoje, encerrados hoje, chamados fora do SLA medido e chamados próximos de vencer.
- A aba **SLA e backlog** exibe uma fila de prioridade operacional para orientar a ordem de atendimento do dia.
- O comando de execução local aponta para `streamlit_app.py`, arquivo principal do projeto.

## Segurança da base

A base Excel está bloqueada no `.gitignore` e não deve ser enviada ao GitHub.


## Gráfico de descrições de problemas

A aba **Detalhamento** possui um gráfico horizontal com as descrições de problemas mais recorrentes. O usuário pode escolher exibir Top 5, 10, 15 ou 20 descrições. Descrições longas são resumidas no eixo e exibidas por completo ao passar o mouse.


## Métricas de suporte adicionadas

- Tempo médio e mediano de resolução em horas úteis.
- Conversão de 1 dia trabalhado para 8 horas.
- Segunda a sexta-feira como dias úteis.
- SLA semanal e percentual dentro do prazo.
- Backlog por faixa de idade.
- Aging médio e aging máximo.
- Chamados por prioridade.
- Chamados abertos por dia da semana.
- Problemas com maior tempo médio de resolução.
- Lista dos chamados pendentes mais antigos.
