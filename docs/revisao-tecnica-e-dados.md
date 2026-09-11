# Revisão técnica e de dados — chamados N2

**Data da revisão:** 11/09/2026

**Escopo:** revisão estática do código, do DDL PostgreSQL/Supabase e das métricas
existentes. A base produtiva não faz parte do repositório e as credenciais locais
são apenas exemplos; portanto, esta revisão **não afirma resultados sobre os
registros reais**. O script `sql/auditoria_base.sql` foi incluído para produzir
esse diagnóstico no ambiente autorizado, sem alterar dados.

## Resumo executivo

O produto já responde bem às perguntas de **volume, backlog, SLA, recorrência,
localização e responsável**. O maior ganho agora não virá de mais gráficos, mas
de três fundamentos:

1. **Confiabilidade da medição:** calendário de atendimento, metas versionadas e
   histórico de eventos; hoje o SLA é recalculado com uma aproximação de 8 horas
   por dia útil e sem feriados.
2. **Governança e segurança:** autenticação individual, autorização no banco,
   trilha de auditoria e classificação/retenção dos textos livres.
3. **Métricas de qualidade e experiência:** primeira resposta, resolução no
   primeiro contato, reabertura e CSAT; o modelo atual guarda somente o retrato
   mais recente do chamado e não permite calcular esses indicadores de forma
   confiável.

Não se recomenda adotar metas genéricas de mercado como verdade operacional.
Primeiro devem ser medidos 60–90 dias de baseline por prioridade, serviço e fila;
depois, SLOs devem ser acordados com o negócio e revistos trimestralmente.

## Achados priorizados do code review

| Prioridade | Achado observado | Risco | Ação objetiva |
|---|---|---|---|
| **P0** | O DDL não habilita RLS nem define políticas; a aplicação lê todas as linhas e a atualização depende de uma única senha compartilhada. | Exposição ou alteração indevida de descrições, soluções, responsáveis e localizações. | Usar login individual (Supabase Auth/SSO), RLS por papel/escopo e chave `service_role` somente no servidor. Rotacionar segredos e registrar usuário, horário e arquivo de cada carga. |
| **P0** | O modelo é um *snapshot*: há uma linha por chamado, sem eventos de status, transferências, respostas ou reaberturas. | Não é possível auditar o fluxo nem calcular primeira resposta, FCR, reabertura e tempo por fila. | Criar `chamado_eventos` append-only com `chamado_id`, tipo, origem/destino, agente e instante; manter `chamados_n2` como estado atual. |
| **P1** | `atualizado_em DEFAULT NOW()` só atua no `INSERT`; o `UPSERT` não atualiza automaticamente esse campo. A tabela `cargas_chamados` existe, mas não é preenchida pelo código. | Data de atualização incorreta e ausência de linhagem da carga. | Adicionar trigger de atualização e gravar início/fim, hash, contagens lidas/aceitas/rejeitadas e usuário em cada carga. |
| **P1** | SLA e aging usam segunda a sexta, 8 h/dia, preservando diferença de relógio e ignorando feriados/jornadas. Metas estão fixas no Python. | Indicadores podem divergir do contrato, sobretudo fora do expediente, em feriados e quando a meta muda. | Criar calendário operacional e tabela de políticas de SLA com vigência, prioridade, serviço, fila e timezone; congelar a política aplicada no chamado. |
| **P1** | A consulta pagina e transfere a tabela inteira ao Streamlit, ordenada somente por `abertura`; filtros e agregações são feitos em memória. | Tempo/custo crescem linearmente e paginação pode ficar instável em atualizações concorrentes ou datas empatadas. | Enviar filtros ao Postgres, criar RPC/view agregada e usar paginação por cursor `(abertura, numero_chamado)`. |
| **P1** | Datas são convertidas para UTC e depois perdem timezone; o cálculo usa o relógio local do processo. | Virada de dia, SLA e agrupamentos podem variar conforme o ambiente. | Definir timezone da operação, manter `TIMESTAMPTZ` até a apresentação e tornar o instante de referência explícito/testável. |
| **P2** | Quase todos os atributos são texto livre e não há `NOT NULL`, `CHECK`, chaves de referência nem índice para equipe/responsável/prioridade/SLA. | Variações cadastrais quebram segmentação; consultas futuras degradam. | Padronizar dimensões e IDs, validar domínios na ingestão e criar índices guiados por `EXPLAIN (ANALYZE, BUFFERS)`, não por suposição. |
| **P2** | O Excel é lido integralmente, sem limite explícito de tamanho, e erros internos são exibidos diretamente na interface. | Consumo excessivo de memória e vazamento de detalhes técnicos. | Limitar upload/linhas/colunas, validar assinatura e esquema antes do processamento; registrar erro técnico e mostrar mensagem sanitizada ao usuário. |
| **P2** | Há import duplicado de `calcular_kpis` e imports executivos sem uso no arquivo principal. A suíte `unittest discover` padrão não encontra testes; não há testes para tratamento, banco, filtros ou segurança. | Manutenção confusa e regressões nas regras críticas. | Remover código morto, padronizar `pytest` no CI e cobrir calendário/SLA, timezone, ingestão inválida, paginação e autorização. |

## O que medir a seguir (ordem recomendada)

### Agora — alto valor, baixa ambiguidade

1. **Backlog por idade, prioridade e serviço**, incluindo P90/P95 de aging.
2. **Entrada, saída e saldo por período**, sempre em coortes separadas (abertos no
   período versus encerrados no período).
3. **SLA elegível e cobertura do SLA**: exibir numerador, denominador e percentual
   sem meta, não apenas a taxa final.
4. **Qualidade cadastral**: completude, valores inválidos, datas incoerentes e
   cardinalidade dos campos. O script de auditoria entregue calcula esse ponto.
5. **Pareto de recorrência**, com dono e prazo de ação para as causas que formam
   80% do volume; gráfico sem ação associada não reduz demanda.

### Próximo ciclo — exige novos dados

| Indicador | Campos/eventos mínimos | Decisão suportada |
|---|---|---|
| Tempo de primeira resposta (mediana, P90) | `primeira_resposta_em`, jornada e canal | Dimensionamento e velocidade de triagem. |
| Resolução no primeiro contato (FCR) | contatos/interações e regra de resolução | Qualidade e autonomia do N1/N2. |
| Reabertura em 7/30 dias | eventos de fechamento e reabertura | Efetividade da solução, sem premiar fechamento precoce. |
| CSAT e taxa de resposta | nota, comentário, convite e resposta | Experiência percebida e viés da amostra. |
| Transferências/escalonamentos | evento, fila anterior/nova e motivo | Roteamento, capacitação e retrabalho. |
| Demanda evitada | canal, artigo usado, autosserviço e deflexão confirmada | Retorno da base de conhecimento/automação. |
| Custo por chamado | tempo ativo, custo/hora e fornecedor | Priorização econômica sem confundir tempo corrido com esforço. |

### Depois — maturidade de gestão

- Relacionar incidente a **serviço/ativo, problema, causa raiz e mudança**.
- Exibir impacto no negócio (usuários afetados, indisponibilidade e criticidade),
  além da quantidade de tickets.
- Prever risco de estouro e capacidade **somente depois** de histórico de eventos,
  qualidade estável e monitoramento de erro/drift.
- Para incidentes causados por software, conectar às métricas de entrega do DORA;
  elas complementam, mas não substituem, SLA e experiência de suporte.

## Modelo de dados alvo (mínimo)

- `chamados`: identidade e estado atual, com `servico_id`, `solicitante_id`
  pseudonimizado, impacto, urgência, prioridade e timestamps com timezone.
- `chamado_eventos`: histórico imutável de criação, resposta, status,
  transferência, resolução, reabertura e comentário.
- `politicas_sla`: versão, vigência, serviço/prioridade, metas de resposta e
  resolução, calendário e regra de pausa.
- `calendarios` / `calendario_excecoes`: timezone, jornada e feriados.
- `cargas`: hash do arquivo, origem, usuário, timestamps e contagens de qualidade.
- Dimensões controladas para serviço, categoria, problema, localização, equipe e
  responsável, evitando usar rótulos livres como chave analítica.

## Plano de 90 dias

### 0–30 dias

- Executar `sql/auditoria_base.sql`, registrar baseline e definir donos para cada
  regra de qualidade.
- Corrigir autenticação/RLS, rotação de segredo e log de carga.
- Formalizar timezone, calendário, elegibilidade e metas de SLA com o negócio.
- Implantar CI com testes e verificação de dependências.

### 31–60 dias

- Criar eventos, políticas de SLA versionadas e dimensões controladas.
- Mover filtros/agregações para o banco e medir consultas com `EXPLAIN`.
- Instrumentar primeira resposta, reabertura, transferências e CSAT.

### 61–90 dias

- Publicar scorecard por serviço/fila com baseline e SLO acordado.
- Associar Pareto a planos de causa raiz e medir redução de recorrência.
- Definir retenção, mascaramento e processo de exclusão/exportação de dados.

## Critérios de aceite

- 100% das cargas têm hash, autor, início/fim e contagens de rejeição.
- Nenhum usuário consulta ou altera dados fora do seu papel em testes de RLS.
- SLA reproduz casos de borda (fora do expediente, fim de semana, feriado,
  pausa e mudança de política) e informa sua cobertura.
- Dashboard não precisa baixar todas as descrições/soluções para mostrar KPIs.
- Cada KPI tem definição, fonte, dono, frequência, numerador e denominador.
- CSAT é exibido junto com taxa de resposta; médias de tempo incluem mediana e
  percentis para reduzir distorção por outliers.

## Referências de mercado usadas como direção

- [Google Cloud — DORA metrics](https://cloud.google.com/devops/state-of-devops):
  conexão entre estabilidade e desempenho de entrega.
- [Atlassian — incident management KPIs](https://www.atlassian.com/incident-management/kpis):
  conjunto de métricas de detecção, resposta e resolução.
- [Zendesk — customer support metrics](https://www.zendesk.com/blog/customer-support-metrics/):
  primeira resposta, resolução, FCR, reabertura e satisfação.
- [PostgreSQL — Row Security Policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html):
  mecanismo recomendado para autorização por linha no banco.
- [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/):
  referência para autenticação, controle de acesso, upload e tratamento de erros.

Essas referências orientam **quais perguntas medir**, não fornecem uma meta
universal. Comparações externas só são válidas quando canal, prioridade, jornada,
complexidade e definição do indicador são equivalentes.
