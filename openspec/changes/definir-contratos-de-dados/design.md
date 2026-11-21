## Context

Ver `proposal.md` (Why). A arquitetura SAD v3 não tem banco nem servidor: o job do GitHub Actions grava arquivos no branch `data` e em `public/`, o calibrador lê o histórico e o site estático lê `public/queue.json` e `public/metrics.json`. Os arquivos são a única interface entre as equipes.

## Goals / Non-Goals

**Goals:**
- Um formato por arquivo, verificável por máquina, que as três equipes possam usar desde já.
- Exemplos realistas que sirvam de dado falso para o Front e de referência para o Back.

**Non-Goals:**
- Implementar coleta, chamadas ao Jev, calibrador ou site.
- Definir a regra fina do gabarito (fica no cartão do Back); o contrato só garante que os campos necessários existam e registra a versão das regras.

## Decisions

**JSON Schema draft 2020-12, um arquivo por contrato.** Valida por máquina e tem biblioteca em Python e JavaScript. Alternativas: dataclasses ou Pydantic (presas ao Python, o Front não usaria) e OpenAPI (feito para APIs HTTP, que não temos). O OpenSpec descreve comportamento e não define formato de dados; os specs apontam para os schemas.

**Para arquivos JSONL, o schema descreve uma linha.** Cada linha é validada sozinha, o que combina com arquivos só de acréscimo.

**Chaves em inglês `snake_case`, valores fixos em inglês.** Combina com os campos do GitHub (`state_reason`, `created_at`) e evita acentos em código. O front-end traduz para exibição:

| Valor | Na tela |
|---|---|
| `attention` | Atenção primeiro |
| `human_review` | Revisão humana |
| `likely_no_action` | Provavelmente sem ação |
| `duplicate` | Duplicata |
| `needs_info` | Falta informação |
| `usage_question` | Pergunta de uso |
| `out_of_scope` | Fora do escopo |

**`schema_version` inteiro em todo registro.** Começa em 1. Campo opcional novo não muda a versão; mudança incompatível muda.

**Respostas do Jev com nomes estáveis por pergunta.** `is_defect`, `actionable`, `enough_info`, `usage_question` (chamada A), `severity` com as 4 probabilidades (chamada A), `in_scope` (chamada B) e `duplicates` (chamada C). B e C são opcionais porque só entram na Fase 4.

**Previsões só com respostas brutas.** Como na proposta, `predictions.jsonl` guarda só o que o Jev respondeu. A saída do calibrador (P(sem ação), motivo, faixa) fica no `queue.json`, com a versão do calibrador. Alternativa descartada: gravar a calibração na previsão, que não funciona num arquivo que nunca é reescrito, já que o calibrador é retreinado.

**`model` em vez de `jev_model`.** A arquitetura prevê a Laya como alternativa local do avaliador; o campo aceita `jev-X.Y.Z` ou `laya-X.Y.Z`, nunca `jev-latest`.

**`mode` na previsão (`backfill` ou `daily`).** O histórico é avaliado depois de a issue fechar, com o texto que existir na época (a proposta pede para registrar essa limitação). Só as primeiras previsões `daily` entram no teste prospectivo.

**Chaves de idempotência.** Previsão: (`repo`, `number`, `body_sha256`, `versions`). Desfecho: (`repo`, `number`, `closed_at`). O job confere antes de acrescentar uma linha.

**Motivo = pergunta ligada a motivo que mais pesou.** `usage_question` → `usage_question`, `enough_info` → `needs_info`, `in_scope` → `out_of_scope`, `duplicates` → `duplicate`. `is_defect`, `actionable` e `severity` entram no calibrador, mas não viram motivo.

**Valores de `state_reason` conferidos na API.** Em 21/11/2026, a busca do GitHub em `microsoft/vscode` devolveu issues fechadas como `completed` (185.261), `not_planned` (51.134) e `duplicate` (4.591); a issue #348744 traz `state_reason: "duplicate"`. O enum fica `completed`, `not_planned`, `duplicate`, `reopened` e `null` (issues antigas, de antes do campo existir).

**Desempate da faixa `attention` por `created_at`, da mais antiga para a mais nova.** A proposta diz só "por severidade e depois por data". Mais antiga primeiro evita que issues graves fiquem esquecidas. Alternativas: mais nova primeiro (triagem diária) ou `updated_at` (atividade recente); como o `queue.json` traz as duas datas, o front pode oferecer essas ordens sem mudar o contrato.

**`input_text` opcional na previsão.** Guarda o texto limpo enviado na chamada A, para o `audit.py` conseguir reproduzir a previsão mesmo se a issue for editada. Opcional por causa do tamanho dos arquivos.

**Validador em Python (`contracts/validate.py`).** Valida os exemplos e, depois, os arquivos reais do job. Usa `jsonschema` e `pyyaml`. A checagem de formato de data é feita por `pattern` (termina em `Z`), sem depender de extensões da biblioteca.

## Risks / Trade-offs

- [Contrato muda muito no começo] → Enquanto nada estiver em produção, ajustes ficam na versão 1; depois, só com nova `schema_version`.
- [Exemplo desatualizado em relação ao schema] → O validador roda nos exemplos; a ideia é rodá-lo também no CI.
- [Front e Back interpretarem um campo de forma diferente] → Cada campo tem `description` em português no schema, e o README de `contracts/` resume quem escreve e quem lê cada arquivo.

## Open Questions

- Granularidade de `metrics.json` por faixa de tamanho de texto (limites dos baldes) pode ser ajustada quando a Fase 5 começar, sem mudar a estrutura.
- Regra fina dos bots. Opções: (A) todo fechamento por bot de inatividade fica fora da conta, como na proposta; (B) bot + label de motivo (`needs-info`, `duplicate`, `question`) conta como `no_action` com esse motivo, e bot sem label fica fora; (C) igual à B, mas só se um humano colocou a label (timeline). Decisão: começar com A (`gab-1`); na Fase 0, medir quantas issues ficam com A e com B, e passar para B (`gab-2`) se algum repositório ficar abaixo do portão de 15%. O contrato atende às três.
