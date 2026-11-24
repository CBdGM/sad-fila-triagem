## Why

O `input_text` de cada previsão guarda o texto da issue. Em 24/11, uma issue pública do VS Code (#338747) trazia um token de acesso do Azure DevOps colado pelo autor, e a proteção de segredos do GitHub bloqueou o push do branch `data`. Se isso acontecer no job diário, o commit falha todo dia até alguém intervir, e o repositório passaria a republicar credenciais de terceiros.

## What Changes

- Antes de gravar, o avaliador troca no `input_text` os trechos com formato de credencial conhecida (tokens do GitHub, Azure DevOps, AWS, OpenAI, Slack, Google) por `[REDACTED]`.
- O texto enviado ao Jev não muda (continua `clean-1`), então as versões e a idempotência ficam como estão; só o registro gravado é redigido.
- O resumo da execução informa quantas previsões tiveram trechos redigidos.

## Capabilities

### New Capabilities

(nenhuma)

### Modified Capabilities

- `perguntas-ao-jev`: `input_text` gravado sem credenciais.

## Impact

- `evaluator/redact.py` (novo), `evaluator/run.py`, `evaluator/__main__.py`, testes.
- Previsões já gravadas não mudam (a do #338747 já foi redigida à mão no branch `data`).
