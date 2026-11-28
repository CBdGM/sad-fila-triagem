## Why

A coleta incremental do GitHub (`/issues?since=`) não informa quando uma issue é transferida para outro repositório, apagada ou convertida em discussão. Ela fica para sempre como "aberta" no `issues.jsonl`. Em 25/11, a grafana/grafana#138549 foi transferida: o Jev passou a pulá-la todo dia (o GitHub responde que ela não existe ali) e a auditoria apontou uma atenção diária, deixando o job vermelho sem que nada novo tivesse acontecido.

## What Changes

- O coletor, ao fim de cada coleta, confere pelo GraphQL (em lotes) se as issues abertas ainda existem no repositório e marca as que sumiram com `gone_at` (quando percebeu). Não apaga a linha: previsões e desfechos dela continuam ligados a uma issue conhecida.
- Se a issue voltar a aparecer na coleta, a linha é regravada e a marca some.
- Uma falha nessa conferência não derruba a coleta: só avisa, e a conferência é refeita no dia seguinte.
- Contrato `issue.schema.json`: campo opcional `gone_at`.
- Avaliador (`daily`), publicação e auditoria tratam issue com `gone_at` como fora das abertas.
- Resumo da coleta e `--changes` informam as sumidas (`gone`).

## Capabilities

### New Capabilities

(nenhuma)

### Modified Capabilities

- `coleta-de-issues`: conferência das abertas e marca `gone_at`.
- `contratos-de-dados`: campo opcional `gone_at` na issue.
- `perguntas-ao-jev`, `publicacao-da-fila`, `auditoria-dos-dados`: issue sumida não conta como aberta.

## Impact

- `collector/collect.py`, `collector/__main__.py`, `contracts/issue.schema.json`, `contracts/README.md`, `evaluator/run.py`, `publisher/build.py`, `audit/checks.py`, testes.
- Custo: ~1 consulta GraphQL por 100 abertas por repositório por dia (~10 por repositório).
