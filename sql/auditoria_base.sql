-- Auditoria somente leitura para PostgreSQL/Supabase.
-- Execute no SQL Editor com um papel autorizado. Cada resultado é independente.

-- 1. Volume, período e atualização observada.
SELECT
    COUNT(*) AS linhas,
    COUNT(DISTINCT numero_chamado) AS chamados_unicos,
    MIN(abertura) AS primeira_abertura,
    MAX(abertura) AS ultima_abertura,
    MIN(atualizado_em) AS primeira_atualizacao,
    MAX(atualizado_em) AS ultima_atualizacao
FROM public.chamados_n2;

-- 2. Completude dos campos que sustentam os indicadores atuais.
SELECT campo, preenchidos, total,
       ROUND(100.0 * preenchidos / NULLIF(total, 0), 2) AS percentual_preenchido
FROM (
    SELECT 'abertura' AS campo, COUNT(abertura) AS preenchidos, COUNT(*) AS total FROM public.chamados_n2
    UNION ALL SELECT 'situacao', COUNT(NULLIF(BTRIM(situacao), '')), COUNT(*) FROM public.chamados_n2
    UNION ALL SELECT 'status_sla', COUNT(NULLIF(BTRIM(status_sla), '')), COUNT(*) FROM public.chamados_n2
    UNION ALL SELECT 'nivelsla', COUNT(NULLIF(BTRIM(nivelsla), '')), COUNT(*) FROM public.chamados_n2
    UNION ALL SELECT 'prioridade', COUNT(NULLIF(BTRIM(prioridade), '')), COUNT(*) FROM public.chamados_n2
    UNION ALL SELECT 'localizacao', COUNT(NULLIF(BTRIM(localizacao), '')), COUNT(*) FROM public.chamados_n2
    UNION ALL SELECT 'problema', COUNT(NULLIF(BTRIM(problema), '')), COUNT(*) FROM public.chamados_n2
    UNION ALL SELECT 'responsavel', COUNT(NULLIF(BTRIM(responsavel), '')), COUNT(*) FROM public.chamados_n2
) AS completude
ORDER BY percentual_preenchido, campo;

-- 3. Integridade temporal. Resultado esperado: zero em todas as regras.
SELECT regra, quantidade
FROM (
    SELECT 'encerramento_anterior_abertura' AS regra, COUNT(*) AS quantidade
    FROM public.chamados_n2
    WHERE encerramento < abertura
    UNION ALL
    SELECT 'abertura_futura', COUNT(*)
    FROM public.chamados_n2
    WHERE abertura > NOW() + INTERVAL '1 day'
    UNION ALL
    SELECT 'encerrado_sem_encerramento', COUNT(*)
    FROM public.chamados_n2
    WHERE LOWER(BTRIM(COALESCE(situacao, ''))) IN
          ('encerrado', 'fechado', 'concluído', 'concluido', 'resolvido', 'finalizado')
      AND encerramento IS NULL
    UNION ALL
    SELECT 'aberto_com_encerramento', COUNT(*)
    FROM public.chamados_n2
    WHERE LOWER(BTRIM(COALESCE(situacao, ''))) NOT IN
          ('encerrado', 'fechado', 'concluído', 'concluido', 'resolvido', 'finalizado')
      AND encerramento IS NOT NULL
) AS inconsistencias
ORDER BY quantidade DESC;

-- 4. Valores de domínio: revela grafias duplicadas e categorias explosivas.
SELECT 'situacao' AS campo, COALESCE(NULLIF(BTRIM(situacao), ''), '<vazio>') AS valor,
       COUNT(*) AS quantidade
FROM public.chamados_n2 GROUP BY 1, 2
UNION ALL
SELECT 'status_sla', COALESCE(NULLIF(BTRIM(status_sla), ''), '<vazio>'), COUNT(*)
FROM public.chamados_n2 GROUP BY 1, 2
UNION ALL
SELECT 'prioridade', COALESCE(NULLIF(BTRIM(prioridade), ''), '<vazio>'), COUNT(*)
FROM public.chamados_n2 GROUP BY 1, 2
UNION ALL
SELECT 'nivelsla', COALESCE(NULLIF(BTRIM(nivelsla), ''), '<vazio>'), COUNT(*)
FROM public.chamados_n2 GROUP BY 1, 2
ORDER BY campo, quantidade DESC, valor;

-- 5. Backlog por prioridade e faixa de idade corrida (triagem; não substitui SLA útil).
WITH backlog AS (
    SELECT prioridade, EXTRACT(EPOCH FROM (NOW() - abertura)) / 86400.0 AS dias
    FROM public.chamados_n2
    WHERE LOWER(BTRIM(COALESCE(situacao, ''))) NOT IN
          ('encerrado', 'fechado', 'concluído', 'concluido', 'resolvido', 'finalizado')
      AND abertura IS NOT NULL
)
SELECT COALESCE(NULLIF(BTRIM(prioridade), ''), '<vazio>') AS prioridade,
       CASE WHEN dias <= 1 THEN '00-01 dia'
            WHEN dias <= 3 THEN '02-03 dias'
            WHEN dias <= 7 THEN '04-07 dias'
            WHEN dias <= 30 THEN '08-30 dias'
            ELSE '31+ dias' END AS faixa,
       COUNT(*) AS quantidade
FROM backlog
GROUP BY 1, 2
ORDER BY 1, 2;

-- 6. Concentração dos problemas (insumo para Pareto e causa raiz).
WITH problemas AS (
    SELECT COALESCE(NULLIF(BTRIM(problema), ''), '<vazio>') AS problema,
           COUNT(*) AS quantidade
    FROM public.chamados_n2
    GROUP BY 1
)
SELECT problema, quantidade,
       ROUND(100.0 * quantidade / SUM(quantidade) OVER (), 2) AS percentual,
       ROUND(100.0 * SUM(quantidade) OVER (ORDER BY quantidade DESC, problema)
             / SUM(quantidade) OVER (), 2) AS percentual_acumulado
FROM problemas
ORDER BY quantidade DESC, problema;

-- 7. Fluxo mensal: demanda e entrega são coortes diferentes.
WITH meses AS (
    SELECT DATE_TRUNC('month', abertura) AS mes FROM public.chamados_n2 WHERE abertura IS NOT NULL
    UNION
    SELECT DATE_TRUNC('month', encerramento) FROM public.chamados_n2 WHERE encerramento IS NOT NULL
), entradas AS (
    SELECT DATE_TRUNC('month', abertura) AS mes, COUNT(*) AS abertos
    FROM public.chamados_n2 WHERE abertura IS NOT NULL GROUP BY 1
), saidas AS (
    SELECT DATE_TRUNC('month', encerramento) AS mes, COUNT(*) AS encerrados
    FROM public.chamados_n2 WHERE encerramento IS NOT NULL GROUP BY 1
)
SELECT meses.mes, COALESCE(entradas.abertos, 0) AS abertos,
       COALESCE(saidas.encerrados, 0) AS encerrados,
       COALESCE(saidas.encerrados, 0) - COALESCE(entradas.abertos, 0) AS saldo
FROM meses
LEFT JOIN entradas USING (mes)
LEFT JOIN saidas USING (mes)
ORDER BY meses.mes;

-- 8. Linhagem disponível das cargas (pode retornar vazio: hoje a aplicação não grava aqui).
SELECT id, nome_arquivo, quantidade_registros, carregado_em
FROM public.cargas_chamados
ORDER BY carregado_em DESC
LIMIT 100;
