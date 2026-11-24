# coleta-de-issues Specification

## Purpose

Obter as issues dos repositórios públicos observados, de forma incremental e só leitura, e manter o estado da coleta, para que o histórico e a fila partam sempre de dados atualizados e auditáveis.

## Requirements

### Requirement: Só leitura e só repositórios configurados
O coletor SHALL apenas ler a API do GitHub, nunca escrever nos repositórios observados, e SHALL coletar só os repositórios com `enabled` diferente de `false` em `repos.yaml`.

#### Scenario: Repositório desabilitado
- **WHEN** um repositório está com `enabled: false` em `repos.yaml`
- **THEN** o coletor não faz nenhuma requisição para ele e não altera seus arquivos

### Requirement: Nome atual do repositório
Antes de coletar, o coletor MUST conferir o nome atual do repositório. Se ele foi renomeado, MUST falhar com uma mensagem que mostre o nome novo, sem gravar nada.

#### Scenario: Repositório renomeado
- **WHEN** `repos.yaml` lista `facebook/react` e o repositório agora se chama `react/react`
- **THEN** a coleta desse repositório falha dizendo para atualizar o nome para `react/react`

### Requirement: Primeira execução com tetos
Sem `state.json`, o coletor MUST baixar as `first_run.open_max` issues abertas mais recentes (por data de criação) e as issues fechadas cujo `closed_at` esteja dentro dos últimos `first_run.closed_months` meses.

#### Scenario: Primeira execução no Airflow
- **WHEN** o coletor roda sem `state.json`, com `open_max: 500` e `closed_months: 6`
- **THEN** `issues.jsonl` tem no máximo 500 issues abertas e todas as fechadas dos últimos 6 meses

### Requirement: Coleta incremental pelo cursor
Com `state.json`, o coletor MUST pedir só as issues atualizadas desde `cursor_since`, em todos os estados, e atualizar `issues.jsonl` com elas.

#### Scenario: Issue fechada desde a última execução
- **WHEN** uma issue aberta fecha entre duas execuções
- **THEN** a execução seguinte atualiza a linha dela com `state: closed`, `closed_at` e `state_reason`

#### Scenario: Issue nova
- **WHEN** uma issue é aberta entre duas execuções
- **THEN** ela entra em `issues.jsonl` com `first_seen_at` igual ao momento da coleta

### Requirement: Pull requests ficam de fora
O coletor MUST descartar os pull requests que a API devolve na mesma lista das issues.

#### Scenario: Lista misturada
- **WHEN** uma página da API traz 93 pull requests e 7 issues
- **THEN** só as 7 issues são gravadas

### Requirement: Uma linha por issue, com primeira vez preservada
`issues.jsonl` MUST ter uma linha por issue. Ao atualizar uma issue já conhecida, o coletor MUST manter o `first_seen_at` original e atualizar os demais campos.

#### Scenario: Issue já vista recebe label
- **WHEN** uma issue já conhecida ganha uma label
- **THEN** a linha dela é atualizada com a label e o `first_seen_at` continua o mesmo

### Requirement: Detecção de texto editado
O coletor MUST calcular `body_sha256` sobre título e corpo e, ao final, informar quais issues são novas, quais tiveram título ou corpo alterado e quais fecharam nesta execução.

#### Scenario: Só comentários novos
- **WHEN** uma issue recebe comentários, mas título e corpo não mudam
- **THEN** ela não aparece como editada, e o Jev não precisa reavaliá-la

#### Scenario: Corpo editado
- **WHEN** o autor edita o corpo de uma issue já avaliada
- **THEN** ela aparece como editada no resultado da execução

### Requirement: Cursor só avança com sucesso
O coletor MUST gravar `state.json` só depois de gravar `issues.jsonl` com sucesso. O novo `cursor_since` MUST ser o início da execução, para não perder issues atualizadas durante ela.

#### Scenario: Falha no meio da coleta
- **WHEN** a coleta falha na página 40 de 90
- **THEN** `issues.jsonl` e `state.json` continuam como estavam e a próxima execução repete a coleta a partir do mesmo cursor

### Requirement: Execução idempotente
Rodar o coletor duas vezes seguidas MUST NOT duplicar issues nem alterar os dados além do que mudou no GitHub.

#### Scenario: Duas execuções seguidas
- **WHEN** o coletor roda duas vezes sem mudanças no GitHub
- **THEN** `issues.jsonl` tem as mesmas issues com os mesmos valores, e o resultado da segunda execução não lista nada como novo, editado ou fechado

### Requirement: Validação antes de gravar
Cada arquivo gerado MUST passar no seu contrato (`issue.schema.json`, `state.schema.json`) antes de substituir o anterior; se não passar, o arquivo anterior MUST continuar intacto.

#### Scenario: Campo fora do contrato
- **WHEN** uma issue gera uma linha que não passa no schema
- **THEN** o coletor falha, mostra o erro e não substitui `issues.jsonl`

### Requirement: Limites da API respeitados
O coletor MUST respeitar os limites de requisição do GitHub: ao atingir o limite, espera até a liberação indicada pela API em vez de falhar; em erro temporário do servidor, tenta de novo com espera crescente, até um número máximo de tentativas.

#### Scenario: Limite secundário
- **WHEN** a API responde 403 ou 429 com `Retry-After: 60`
- **THEN** o coletor espera 60 segundos e repete a mesma requisição

### Requirement: Nenhum segredo em arquivo
O token do GitHub MUST vir de `GITHUB_TOKEN` ou do `gh auth token`, nunca de arquivo versionado, e MUST NOT aparecer nos arquivos gerados nem nas mensagens de erro.

#### Scenario: Erro de autenticação
- **WHEN** o token é inválido
- **THEN** a mensagem de erro diz que a autenticação falhou, sem mostrar o token
