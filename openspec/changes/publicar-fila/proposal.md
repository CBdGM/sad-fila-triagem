## Why

O Front precisa de dado real para montar o site, e o calibrador do Back ainda não existe. O card "Publicar queue.json e metrics.json" pede publicar desde já a fila com todas as issues em `human_review`, para o Front trabalhar em paralelo. O GitHub Pages já está ativo e o job diário já atualiza issues e previsões no branch `data`.

## What Changes

- Novo passo de publicação (`publisher/`, `python -m publisher`) que monta, a partir do branch `data`:
  - `public/queue.json` (contrato `queue.schema.json`): as issues abertas que já têm previsão do Jev, com título, link, labels, datas e a severidade do Jev, todas na faixa `human_review`, com `p_no_action` e `reason` nulos e `calibrator: null`;
  - `public/metrics.json` (contrato `metrics.schema.json`) com `evaluations` vazio, até o Back calcular as métricas;
  - um `index.html` mínimo com links para os dois arquivos, até o site do Front existir.
- Os dois JSON são validados antes de gravar; se não passarem, nada é publicado e o site anterior continua.
- O job diário ganha um segundo job que publica `public/` no GitHub Pages depois do commit no branch `data`.

## Capabilities

### New Capabilities

- `publicacao-da-fila`: montagem e publicação de `queue.json` e `metrics.json`.

### Modified Capabilities

(nenhuma)

## Impact

- Código novo: `publisher/`, `tests/publisher/`; `.github/workflows/daily.yml` ganha o job de publicação.
- Lê `repos.yaml` e, por repositório, `issues.jsonl`, `state.json` e `predictions.jsonl`. Não grava no branch `data`.
- Fora deste change: calibrador, cortes das faixas, `contributions` e métricas (Back); o site (Front).
