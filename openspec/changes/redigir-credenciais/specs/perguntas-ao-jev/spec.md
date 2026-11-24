## ADDED Requirements

### Requirement: Texto gravado sem credenciais

Antes de gravar a previsão, o passo SHALL trocar no `input_text` os trechos com formato de credencial conhecida por `[REDACTED]`. O texto enviado ao Jev e o `body_sha256` SHALL continuar os mesmos.

#### Scenario: Issue com token colado
- **WHEN** o texto de uma issue contém um token de acesso do GitHub
- **THEN** o `input_text` gravado tem `[REDACTED]` no lugar do token, o Jev recebeu o texto original e o resumo conta uma previsão redigida

#### Scenario: Issue sem credencial
- **WHEN** o texto não contém nenhum padrão de credencial
- **THEN** o `input_text` gravado é idêntico ao texto enviado ao Jev
