## ADDED Requirements

### Requirement: Erros de integridade

A auditoria SHALL apontar como erro: linha que não passa no contrato do arquivo, desfecho repetido (mesmo `number` e `closed_at`), previsão repetida (mesmo `number`, `body_sha256` e versões), issue com mais de uma previsão `first_seen` e previsão de issue que não está em `issues.jsonl`.

#### Scenario: Previsão repetida
- **WHEN** `predictions.jsonl` tem duas linhas com a mesma chave
- **THEN** a auditoria aponta um erro naquele repositório e sai com código 2

#### Scenario: Dados íntegros
- **WHEN** nenhum arquivo tem problema
- **THEN** a auditoria sai com código 0

### Requirement: Atenções de atualização

A auditoria SHALL apontar como atenção: repositório cuja última coleta bem-sucedida passou do limite de horas, issue fechada sem desfecho para aquele fechamento, issue aberta vista há mais dias que o limite sem nenhuma previsão, e pasta de dados acima do limite de tamanho.

#### Scenario: Coleta parada
- **WHEN** o `last_success_at` de um repositório é de 3 dias atrás e o limite é 36 horas
- **THEN** a auditoria aponta uma atenção naquele repositório e sai com código 1

#### Scenario: Aberta recente sem previsão
- **WHEN** uma issue aberta foi vista há 1 dia e ainda não tem previsão
- **THEN** a auditoria não aponta nada sobre ela

### Requirement: Publicação bloqueada só por erro

No job diário, a auditoria SHALL rodar depois da atualização do branch `data` e antes da publicação. Qualquer achado SHALL deixar o job com falha; só erros SHALL impedir a publicação da fila.

#### Scenario: Só atenções
- **WHEN** a auditoria encontra apenas atenções
- **THEN** o job fica com falha e a fila é publicada mesmo assim

#### Scenario: Erro
- **WHEN** a auditoria encontra um erro
- **THEN** a fila não é publicada e o site continua com a versão anterior
