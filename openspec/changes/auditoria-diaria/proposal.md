## Why

O job diário roda sozinho e grava no branch `data` todo dia. Uma auditoria manual em 24/11 confirmou que os dados estão íntegros, mas nada avisa se isso mudar: um repositório que para de coletar, um bug de idempotência ou o Jev que deixa de avaliar só seriam notados semanas depois. Falhas de dados também não deveriam chegar à fila publicada.

## What Changes

- Novo passo de auditoria (`audit/`, `python -m audit`) que confere o branch `data` sem chamar nenhuma API:
  - **erros** (dados corrompidos): linha fora do contrato, desfecho ou previsão repetidos, mais de um `first_seen` por issue, previsão de issue desconhecida;
  - **atenções** (dados parados ou crescendo): última coleta bem-sucedida há mais de 36 horas, issue fechada sem desfecho, issue aberta vista há mais de 4 dias sem previsão do Jev, branch `data` acima de 150 MB.
- Código de saída: 0 sem achados, 1 só atenções, 2 com algum erro. O resumo vai para o log.
- No job diário, a auditoria vira um job entre `diario` e `publicar`. Qualquer achado deixa o job vermelho (o GitHub avisa por e-mail); só **erros** impedem a publicação, então a fila do dia anterior continua no ar quando os dados estão corrompidos.

## Capabilities

### New Capabilities

- `auditoria-dos-dados`: checagens diárias de integridade e de atualização do branch `data`.

### Modified Capabilities

(nenhuma)

## Impact

- Código novo: `audit/`, `tests/audit/`; `.github/workflows/daily.yml` ganha o job `auditar` e `publicar` passa a depender dele.
- Só lê o branch `data` e o `repos.yaml`; não grava nada.
- Fora deste change: checagens semanais contra o GitHub (contagens pela busca, amostra de desfechos), que podem vir depois num workflow próprio.
