# contratos-de-dados Specification

## Purpose

Define o formato, o versionamento e a validação dos arquivos que o job, o calibrador e o front-end trocam entre si, para que as equipes trabalhem em paralelo sem quebrar umas às outras.

## Requirements

### Requirement: Schema e exemplo para cada arquivo trocado
O projeto SHALL manter em `contracts/` um JSON Schema e um arquivo de exemplo válido para cada arquivo trocado entre componentes: `repos.yaml`, `state.json`, `issues.jsonl`, `predictions.jsonl`, `outcomes.jsonl`, `queue.json` e `metrics.json`.

#### Scenario: Exemplo confere com o schema
- **WHEN** o validador roda sobre os exemplos de `contracts/`
- **THEN** todos os exemplos passam sem erro

#### Scenario: Arquivo sem contrato
- **WHEN** um componente passa a gravar um arquivo novo lido por outro componente
- **THEN** o schema e o exemplo desse arquivo entram em `contracts/` no mesmo change

### Requirement: Versão do schema em todo registro
Todo objeto de nível superior e toda linha de arquivo JSONL MUST ter o campo `schema_version`. Uma mudança incompatível (campo removido, renomeado ou com tipo diferente) MUST aumentar esse número.

#### Scenario: Registro sem versão
- **WHEN** uma linha de `predictions.jsonl` não tem `schema_version`
- **THEN** o validador rejeita a linha

#### Scenario: Campo novo opcional
- **WHEN** um campo opcional é acrescentado a um schema
- **THEN** a `schema_version` pode continuar a mesma

### Requirement: Convenções de nomes, datas e valores fixos
As chaves MUST estar em inglês `snake_case`, as datas MUST estar em UTC no formato RFC 3339 e os motivos e faixas MUST usar apenas os valores fixos definidos nos schemas. Textos exibidos ao usuário ficam a cargo do front-end.

#### Scenario: Motivo fora da lista
- **WHEN** um registro traz o motivo `spam`, que não está na lista
- **THEN** o validador rejeita o registro

#### Scenario: Data com fuso horário local
- **WHEN** uma data vem como `2026-11-21T09:00:00-03:00`
- **THEN** o validador rejeita a data, que precisa terminar em `Z`

### Requirement: Validação antes de gravar
Um componente MUST validar cada arquivo contra o seu schema antes de gravá-lo no branch `data` ou em `public/`. Se a validação falhar, o arquivo anterior MUST continuar intacto.

#### Scenario: Fila inválida
- **WHEN** o job gera um `queue.json` que não passa no schema
- **THEN** o job falha sem sobrescrever o `queue.json` publicado

### Requirement: Previsões e desfechos só acrescentam
`predictions.jsonl` e `outcomes.jsonl` MUST ser só de acréscimo: nenhuma linha é editada nem apagada. Uma previsão nova (outro modelo, outras perguntas ou texto editado) MUST virar uma linha nova.

#### Scenario: Troca de versão do Jev
- **WHEN** a versão fixa do Jev muda e uma issue é avaliada de novo
- **THEN** uma linha nova entra em `predictions.jsonl` e a linha antiga continua igual

### Requirement: Primeira previsão congelada
Cada previsão MUST indicar se é a primeira vez que o sistema vê aquela issue (`first_seen`) e se veio do histórico (`backfill`) ou do job diário (`daily`). A primeira previsão de cada issue fica congelada; só as primeiras previsões `daily` contam no teste prospectivo.

#### Scenario: Issue editada depois de avaliada
- **WHEN** o corpo de uma issue já avaliada muda e o Jev é chamado de novo
- **THEN** a nova linha tem `first_seen: false` e a primeira continua sendo a usada na avaliação

#### Scenario: Issue do histórico
- **WHEN** a primeira execução avalia uma issue já fechada
- **THEN** a linha tem `mode: backfill` e não entra no teste prospectivo

### Requirement: Gravação idempotente
Rodar o job duas vezes ou pular um dia MUST NOT duplicar registros: uma previsão com o mesmo repositório, número, hash do texto e versões não é gravada de novo, e um desfecho com o mesmo repositório, número e data de fechamento também não.

#### Scenario: Job executado duas vezes no mesmo dia
- **WHEN** o job roda de novo sem nenhuma issue ter mudado
- **THEN** `predictions.jsonl` e `outcomes.jsonl` continuam com as mesmas linhas

### Requirement: Procedência de cada previsão
Cada previsão MUST registrar a versão do modelo pedida, o `served_by` devolvido, o `request_id` quando o avaliador o devolve (o Jev devolve; a Laya, local, não), a versão das perguntas, a versão da limpeza e o hash do texto avaliado.

#### Scenario: Auditoria de uma previsão
- **WHEN** alguém precisa reproduzir uma previsão antiga
- **THEN** a linha informa qual modelo respondeu, com quais perguntas e sobre qual versão do texto

### Requirement: Desfecho de cada issue fechada
Para cada issue fechada, `outcomes.jsonl` MUST registrar o `state_reason`, as labels no fechamento, quem fechou e se era bot, o PR mesclado ligado (se houver) e a classificação do gabarito: `no_action`, `action` ou `excluded`, com a versão das regras usadas.

#### Scenario: Issue fechada como duplicata
- **WHEN** uma issue fecha com `state_reason` `duplicate`
- **THEN** o desfecho é `no_action` com motivo `duplicate`

#### Scenario: Fechada por bot de inatividade
- **WHEN** uma conta listada em `stale_bots` fecha a issue
- **THEN** o desfecho é `excluded` com `exclusion_reason` `stale_bot`

#### Scenario: Fechada com label de inatividade
- **WHEN** a issue fecha com uma label listada em `stale_labels` (ex.: `lifecycle/rotten`), mesmo que a conta que fechou também feche a pedido de humanos
- **THEN** o desfecho é `excluded` com `exclusion_reason` `stale_bot`

#### Scenario: Fechada como completed sem PR
- **WHEN** a issue fecha como `completed` sem PR mesclado ligado
- **THEN** o desfecho é `excluded` com `exclusion_reason` `completed_without_pr`

### Requirement: Toda issue aberta aparece na fila
`queue.json` MUST trazer cada issue aberta observada em exatamente uma das faixas `attention`, `human_review` ou `likely_no_action`. A fila nunca esconde issues.

#### Scenario: Calibrador ainda não treinado
- **WHEN** o job roda antes de existir um calibrador
- **THEN** as issues vão para `human_review`, com `p_no_action` nulo

#### Scenario: Issue fechada
- **WHEN** uma issue fecha entre duas execuções
- **THEN** ela sai do `queue.json` da execução seguinte

### Requirement: Motivo e evidência na fila
Cada item da faixa `likely_no_action` MUST ter um motivo principal (`duplicate`, `needs_info`, `usage_question` ou `out_of_scope`), que é a pergunta ligada a um motivo que mais pesou no calibrador, e pelo menos uma evidência. Quando o motivo for `duplicate`, a evidência MUST trazer o link da issue candidata.

#### Scenario: Provável duplicata
- **WHEN** uma issue cai em `likely_no_action` por duplicata
- **THEN** o item traz `reason: duplicate` e uma evidência com o número e a URL da outra issue

### Requirement: Data da última atualização
`queue.json` MUST trazer `generated_at` e, por repositório, a data da última execução bem-sucedida, para o front-end mostrar se a fila está desatualizada. `metrics.json` MUST trazer `generated_at`.

#### Scenario: Agendamento pulado
- **WHEN** o GitHub pula a execução de um dia
- **THEN** o front-end mostra a data da última execução bem-sucedida
