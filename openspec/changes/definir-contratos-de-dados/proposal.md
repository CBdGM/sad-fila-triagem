## Why

Back, Integração e Front vão trabalhar em paralelo sobre os mesmos arquivos (o job grava, o calibrador lê, o site mostra). Sem um formato combinado antes, cada equipe inventa o seu e a integração quebra no fim. Definir os contratos agora destrava as três: o Front começa com dados de exemplo, o Back sabe o que recebe e a Integração sabe o que gravar.

## What Changes

- Pasta `contracts/` com um JSON Schema e um arquivo de exemplo para cada arquivo trocado entre componentes, conforme a proposta de arquitetura SAD v3:
  - `repos.yaml`: repositórios observados, mapa de labels de fechamento e tetos.
  - `data/<repo>/state.json`: cursor `since` e versões em uso.
  - `data/<repo>/issues.jsonl`: uma linha por issue.
  - `data/<repo>/predictions.jsonl`: respostas do Jev, só acrescenta.
  - `data/<repo>/outcomes.jsonl`: como cada issue fechou (gabarito), só acrescenta.
  - `public/queue.json`: a fila para o front-end.
  - `public/metrics.json`: as métricas para o front-end.
- Um script que valida qualquer arquivo de dados contra o seu schema, usado nos exemplos agora e pelo job depois.
- Convenções comuns: chaves em inglês `snake_case`, datas em UTC (RFC 3339), `schema_version` em todo registro, motivos e faixas como valores fixos.

## Capabilities

### New Capabilities

- `contratos-de-dados`: formato, versionamento e validação dos arquivos trocados entre coleta, avaliação, calibração, fila e front-end.

### Modified Capabilities

(nenhuma; é a primeira capability do projeto)

## Impact

- Código novo: `contracts/` (schemas, exemplos, validador e README) e dependências de desenvolvimento (`jsonschema`, `pyyaml`).
- Todas as equipes passam a depender destes formatos. Mudança incompatível num contrato exige nova `schema_version` e um novo change do OpenSpec.
- Nenhum código de coleta, avaliação ou front-end é escrito aqui; isso fica para os changes de cada fase.
