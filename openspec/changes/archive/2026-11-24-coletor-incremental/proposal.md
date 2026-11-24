## Why

Tudo na arquitetura SAD v3 depende de ter as issues coletadas: a Fase 0 do Back precisa das issues fechadas dos últimos 6 meses para auditar o gabarito, e o job diário precisa saber o que é novo, o que foi editado e o que fechou. Hoje só existe o `fetch_issues.py` da PoC, que baixa issues rotuladas por busca e não faz coleta incremental.

## What Changes

- Novo coletor (`collector/`) que, para cada repositório habilitado em `repos.yaml`:
  - na **primeira execução**, baixa as N issues abertas mais recentes e as fechadas dos últimos M meses (tetos do `repos.yaml`);
  - nas **seguintes**, baixa só as issues atualizadas desde o cursor (`since`), o que captura novas, editadas e fechadas;
  - descarta pull requests;
  - grava `data/<repo>/issues.jsonl` e `data/<repo>/state.json` no formato dos contratos, validando antes de gravar;
  - devolve o que mudou na execução (novas, com texto editado, fechadas), para os passos seguintes do job.
- Cliente HTTP do GitHub com paginação por `Link`, tratamento dos limites de requisição (primário e secundário) e repetição em erro temporário.
- Linha de comando: `python -m collector` (um repositório ou todos), usada à mão agora e pelo job depois.
- Testes sem rede, com respostas gravadas da API.

## Capabilities

### New Capabilities

- `coleta-de-issues`: obtenção incremental das issues de repositórios públicos do GitHub e manutenção do estado da coleta.

### Modified Capabilities

(nenhuma; os formatos seguem a capability `contratos-de-dados`, sem mudança)

## Impact

- Código novo: `collector/` e `tests/collector/`; dependências `requests` e `python-dotenv` (as de contrato já existem).
- Reaproveita da PoC (`sad-poc-decisao/fetch_issues.py`): leitura do token (`GITHUB_TOKEN` ou `gh auth token`), sessão HTTP e checagem do nome atual do repositório.
- Fora deste change: desfechos (`outcomes.jsonl`, com quem fechou e PR ligado), avaliação pelo Jev e o workflow do Actions; cada um tem cartão próprio e usa a saída deste coletor.
