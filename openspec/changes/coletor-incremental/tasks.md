# Tasks

## 1. Base

- [ ] 1.1 Criar `requirements.txt` com `requests`, `python-dotenv`, `pyyaml` e `jsonschema`, e `pytest` em `requirements-dev.txt`; verificar a instalação num venv limpo
- [ ] 1.2 Criar o pacote `collector/` (`__init__`, `__main__`, `github`, `collect`, `store`) e `tests/collector/`, e verificar que `python -m collector --help` roda

## 2. Cliente do GitHub (`github.py`)

- [ ] 2.1 Token por `GITHUB_TOKEN` ou `gh auth token` e sessão HTTP, reaproveitando a PoC; verificar com teste que o token nunca aparece em mensagens de erro
- [ ] 2.2 `get` com limite primário, limite secundário (`Retry-After`) e repetição em 5xx; verificar com testes que simulam 403/429/502
- [ ] 2.3 `paginate` seguindo `Link: rel="next"`, com teto de páginas; verificar com teste de 3 páginas gravadas
- [ ] 2.4 Conferência do nome atual do repositório; verificar com teste que um repositório renomeado falha mostrando o nome novo

## 3. Gravação (`store.py`)

- [ ] 3.1 Ler `issues.jsonl` para um dicionário por número e ler `state.json`; verificar com arquivos de exemplo dos contratos
- [ ] 3.2 Gravação atômica com validação pelos schemas de `contracts/`; verificar com teste que uma linha inválida não substitui o arquivo anterior

## 4. Coleta (`collect.py`)

- [ ] 4.1 Conversão de um item da API para uma linha do contrato `issue.schema.json` (com `body_sha256`), descartando PRs; verificar com teste de página misturada
- [ ] 4.2 Primeira execução: abertas até `open_max` e fechadas dentro de `closed_months`; verificar com teste dos dois tetos
- [ ] 4.3 Execução incremental com `since`, preservando `first_seen_at` e calculando `new`, `edited` e `closed`; verificar com testes de issue nova, editada, só comentada e fechada
- [ ] 4.4 Cursor e `last_success_at` gravados só no fim com sucesso; verificar com teste de falha no meio da paginação
- [ ] 4.5 Idempotência; verificar com teste de duas execuções seguidas sem mudanças

## 5. Linha de comando e documentação

- [ ] 5.1 `python -m collector` com `--repo`, `--config`, `--data-dir` e `--changes`, coletando só repositórios habilitados; verificar rodando com `contracts/examples/repos.yaml` adaptado num diretório temporário
- [ ] 5.2 Seção "Coletor" no `README.md` com uso, token e o que cada arquivo recebe; verificar que os comandos documentados rodam como escritos

## 6. Verificação real

- [ ] 6.1 Rodar a primeira execução em um repositório candidato com tetos pequenos (ex.: `open_max: 20`, `closed_months: 1`), conferir `contracts/validate.py` nos arquivos gerados e rodar de novo para confirmar que nada duplica

## Workflow follow-up

- Revisão do time no PR antes de aplicar.
- Arquivar o change com `openspec archive coletor-incremental` depois do merge.
