## Decisions

**Marcar em vez de apagar.** Apagar a linha faria a auditoria ver previsões de "issue fora do `issues.jsonl`", que é erro de dado corrompido e bloquearia a publicação. A marca preserva o histórico e é simples para quem lê: aberta = `state == "open"` sem `gone_at` (`collector.collect.is_open`).

**Como saber que sumiu.** Consulta GraphQL `issue(number: N)` no repositório: o GitHub devolve nulo (`NOT_FOUND`) para issue transferida, apagada ou convertida em discussão. Lotes de 100 aliases por consulta, só para as abertas ainda não marcadas.

**Volta automática.** Uma issue marcada que reaparece na coleta incremental é regravada por `to_record`, que não tem `gone_at`.

**Não derrubar a coleta.** A conferência é um extra: erro do GitHub nela vira aviso e a coleta grava normalmente; o cursor avança como antes.

## Risks / Trade-offs

- [Falso "sumiu" por instabilidade do GraphQL] → só `NOT_FOUND` explícito marca; outros erros não marcam nada.
- [Custo] → ~10 consultas por repositório por dia, dentro do limite de 1.000 pontos/hora do token do Actions.
