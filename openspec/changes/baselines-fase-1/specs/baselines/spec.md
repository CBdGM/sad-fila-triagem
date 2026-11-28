## ADDED Requirements

### Requirement: Conjunto rotulado sem vazamento

O passo SHALL rotular como positivo o desfecho `no_action` e como negativo o `action` do fechamento atual de cada issue, SHALL excluir `excluded`, e SHALL usar como texto o `input_text` das previsões de backfill.

#### Scenario: Desfecho fora da conta
- **WHEN** uma issue tem desfecho `excluded`
- **THEN** ela não entra no conjunto

#### Scenario: Issue reaberta
- **WHEN** o desfecho guardado é de um fechamento anterior ao `closed_at` atual
- **THEN** a issue não entra no conjunto

### Requirement: Corte temporal

O conjunto de cada repositório SHALL ser ordenado por `created_at`, com as 70% mais antigas no treino e as 30% mais recentes no teste. Toda escolha de parâmetro e de corte SHALL usar só o treino.

#### Scenario: Teste mais recente
- **WHEN** o corte é feito
- **THEN** nenhuma issue do treino foi criada depois da issue mais antiga do teste do mesmo repositório

### Requirement: Modelos comparados

O passo SHALL avaliar nos mesmos testes: heurística por regras fixas, heurística com pesos aprendidos, TF-IDF + regressão logística, `1 − is_defect` do Jev e regressão logística sobre as respostas do Jev.

#### Scenario: Regras fixas não treinam
- **WHEN** a heurística por regras fixas é avaliada
- **THEN** sua pontuação depende só do texto da issue, sem nenhum parâmetro aprendido

### Requirement: Métricas

Para cada modelo e repositório, o passo SHALL medir AUC com intervalo de 95% por bootstrap, precisão média, taxa-base e, para modelos com probabilidade, Brier. Precisão, recall e cobertura SHALL usar o menor corte com precisão ≥ 0,90 nas previsões de validação cruzada do treino, e SHALL ficar nulas se o treino não atingir 0,90.

#### Scenario: Precisão-alvo inatingível
- **WHEN** nenhum corte atinge precisão 0,90 no treino
- **THEN** precisão, recall e cobertura do modelo ficam nulas no relatório

### Requirement: Saída no formato do contrato

O passo SHALL gravar um relatório em Markdown e as avaliações num documento válido pelo `metrics.schema.json`, com `design: temporal`.

#### Scenario: Validação
- **WHEN** o passo termina
- **THEN** o JSON gravado passa no `contracts/validate.py metrics`
