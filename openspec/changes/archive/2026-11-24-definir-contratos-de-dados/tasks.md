# Tasks

## 1. Base

- [x] 1.1 Criar `requirements-dev.txt` com `jsonschema` e `pyyaml` e verificar que `pip install -r requirements-dev.txt` funciona num venv
- [x] 1.2 Criar `contracts/validate.py`, que valida JSON, JSONL e YAML contra um schema, e verificar que ele rejeita um arquivo inválido de teste

## 2. Contratos do histórico (Integração e Back)

- [x] 2.1 `repos.schema.json` + `examples/repos.yaml` e verificar com o validador
- [x] 2.2 `state.schema.json` + `examples/state.json` e verificar com o validador
- [x] 2.3 `issue.schema.json` + `examples/issues.jsonl` e verificar com o validador
- [x] 2.4 `prediction.schema.json` + `examples/predictions.jsonl` (modos `daily` e `backfill`, com chamada C) e verificar com o validador
- [x] 2.5 `outcome.schema.json` + `examples/outcomes.jsonl` (um caso de `no_action`, `action` e `excluded`) e verificar com o validador

## 3. Contratos publicados (Front)

- [x] 3.1 `queue.schema.json` + `examples/queue.json` com as três faixas e verificar com o validador
- [x] 3.2 `metrics.schema.json` + `examples/metrics.json` e verificar com o validador

## 4. Documentação

- [x] 4.1 `contracts/README.md` com a tabela de arquivos (quem escreve, quem lê, schema, exemplo), as convenções e a tradução dos valores fixos, e verificar que o comando de validação descrito roda como escrito
- [x] 4.2 Atualizar o `README.md` da raiz com o objetivo do projeto, a estrutura, o uso do OpenSpec e o link para a PoC

## Workflow follow-up

- Revisão do time (Back, Integração e Front) antes de arquivar.
- Arquivar o change com `openspec archive definir-contratos-de-dados` depois da revisão.
