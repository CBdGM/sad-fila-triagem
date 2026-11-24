## Context

O GitHub bloqueia push com segredos conhecidos (push protection). O `input_text` é opcional no contrato e serve para reproduzir a previsão; o hash do corpo (`body_sha256`) é calculado sobre o texto cru e não muda.

## Decisions

**Redigir só o que é gravado.** O Jev continua recebendo o texto `clean-1`. Redigir o texto enviado mudaria a limpeza (subir para `clean-2`) e reavaliaria todo o histórico pela chave de idempotência, por causa de um caso raro. A diferença fica registrada: o `input_text` pode ter `[REDACTED]` onde o texto enviado tinha a credencial.

**Padrões explícitos e conservadores**, com prefixos ou formatos fixos: `ghp_`/`gho_`/`ghu_`/`ghs_`/`ghr_` e `github_pat_` (GitHub), 52 caracteres base32 minúsculos e o formato novo com `AZDO` (Azure DevOps), `AKIA` (AWS), `sk-` (OpenAI e similares), `xox?-` (Slack), `AIza` (Google). O de 52 caracteres base32 é o mais genérico; um falso positivo só apaga um trecho do texto guardado, sem efeito na previsão.

## Risks / Trade-offs

- [Credencial em formato não coberto] → o push do job ainda pode ser bloqueado; o job falha visivelmente e o padrão é acrescentado aqui.
- [Falso positivo] → perde-se um trecho do `input_text`; previsão e hash intactos.
