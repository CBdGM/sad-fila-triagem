# coleta-de-desfechos Specification

## Purpose

Registrar como cada issue observada foi fechada (quem fechou, se foi bot, PR mesclado ligado e a classe do gabarito), para que a Fase 0, o calibrador e a avaliação usem o que os mantenedores de fato fizeram.

## Requirements

### Requirement: Desfecho para cada fechamento ainda sem registro
Para cada issue fechada em `issues.jsonl`, o passo de desfechos SHALL gravar uma linha em `outcomes.jsonl` se ainda não existir linha com o mesmo `number` e `closed_at`.

#### Scenario: Issue fechada pela primeira vez
- **WHEN** `issues.jsonl` tem a issue 74851 fechada e `outcomes.jsonl` não tem linha para ela
- **THEN** a execução acrescenta uma linha para a 74851

#### Scenario: Issue reaberta e fechada de novo
- **WHEN** uma issue já tem desfecho, é reaberta e fecha de novo com outro `closed_at`
- **THEN** uma linha nova é acrescentada e a antiga continua igual

### Requirement: Fatos vindos do GitHub
Cada linha MUST trazer o `state_reason` e as labels da issue, o login de quem fechou, se essa conta é bot e o número do PR mesclado ligado à issue no mesmo repositório (ou nulo).

#### Scenario: Fechada por um PR
- **WHEN** a issue foi fechada pelo merge de um PR do mesmo repositório
- **THEN** `merged_pr` traz o número desse PR

#### Scenario: Fechada por bot
- **WHEN** quem fechou é uma conta de bot
- **THEN** `closed_by_bot` é `true` e `closed_by` usa o login no formato da API REST (ex.: `github-actions[bot]`), o mesmo do `repos.yaml`

### Requirement: PR ligado só se mesclado e do mesmo repositório
`merged_pr` MUST considerar apenas PRs mesclados do próprio repositório: primeiro o PR que fechou a issue; se não houver, o primeiro PR mesclado que referencia a issue.

#### Scenario: PR referenciado mas não mesclado
- **WHEN** a issue foi fechada à mão e o único PR que a referencia não foi mesclado
- **THEN** `merged_pr` é nulo

#### Scenario: PR de outro repositório
- **WHEN** um PR mesclado de outro repositório referencia a issue
- **THEN** ele não conta como `merged_pr`

### Requirement: Só acrescenta e é idempotente
`outcomes.jsonl` MUST ser só de acréscimo, e rodar o passo duas vezes MUST NOT repetir linhas.

#### Scenario: Duas execuções seguidas
- **WHEN** o passo roda duas vezes sem issues novas fechadas
- **THEN** `outcomes.jsonl` fica igual

### Requirement: Progresso preservado em lotes
O passo MUST gravar os desfechos a cada lote processado, para que uma falha no meio não perca os lotes já concluídos, e MUST aceitar um teto de issues por execução.

#### Scenario: Falha no terceiro lote
- **WHEN** a API falha no terceiro de dez lotes
- **THEN** os dois primeiros lotes ficam gravados e a próxima execução continua dos que faltam

#### Scenario: Teto por execução
- **WHEN** há 1.280 issues pendentes e o teto é 200
- **THEN** a execução grava 200 desfechos e deixa o resto para a próxima

### Requirement: Validação antes de gravar
Cada linha MUST passar no contrato `outcome.schema.json` antes de entrar no arquivo; se alguma falhar, o arquivo anterior MUST continuar intacto.

#### Scenario: Linha fora do contrato
- **WHEN** uma linha gerada não passa no schema
- **THEN** o lote não é gravado e o erro aparece com o número da issue

### Requirement: Resumo para a Fase 0
Ao final, o passo MUST mostrar por repositório quantos desfechos existem em cada classe e a porcentagem de `no_action` entre `no_action` e `action`.

#### Scenario: Resumo do Airflow
- **WHEN** o passo termina para `apache/airflow`
- **THEN** o resumo mostra os totais de `no_action`, `action` e `excluded` e a porcentagem "sem ação"
