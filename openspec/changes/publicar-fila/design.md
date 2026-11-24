## Context

O contrato `queue.schema.json` diz que toda issue aberta observada aparece em exatamente uma faixa, e exige em cada item a `severity` do Jev. O job avalia no máximo 200 abertas por repositório por dia, então nos primeiros dias parte das abertas ainda não tem previsão.

## Goals / Non-Goals

**Goals:** fila e métricas válidas pelos contratos, publicadas todo dia no Pages; nada publicado se o contrato falhar.

**Non-Goals:** calibrar, escolher faixas, calcular métricas (Back); o site (Front).

## Decisions

**Só entram as abertas com previsão.** Sem previsão não há `severity`, que o contrato exige. A cobertura completa vem em 2 a 3 dias de job (cerca de 500 abertas por repositório). O resumo da execução informa quantas abertas ficaram fora por falta de previsão. Alternativa descartada: inventar uma severidade padrão, que o Front exibiria como se fosse do Jev.

**Previsão usada: a mais recente da issue** (a de `predicted_at` maior). Se a issue foi editada, vale a avaliação do texto atual; a primeira, congelada, continua no `predictions.jsonl` para a avaliação.

**Sem calibrador, tudo em `human_review`**, com `p_no_action: null`, `reason: null`, `evidence: []` e `calibrator: null` por repositório, como o contrato prevê. Quando o calibrador existir, ele entra antes da montagem e preenche esses campos.

**Ordem:** severidade da mais alta para a mais baixa e, dentro dela, `created_at` da mais antiga para a mais nova (a ordem que o contrato define para `attention`, aplicada também a `human_review` enquanto só existe essa faixa).

**Validar antes de gravar.** `queue.json` e `metrics.json` passam pelo contrato antes de qualquer escrita em `public/`; se um falhar, o comando sai com erro, nada é gravado e o deploy do Pages não acontece, então o site anterior continua no ar.

**Publicação num job separado do workflow diário** (`needs` do job de dados), com as permissões `pages: write` e `id-token: write` só nele. O job de dados continua só com `contents: write`.

## Risks / Trade-offs

- [Fila incompleta nos primeiros dias] → resumo mostra quantas abertas faltam; cobertura completa em poucos dias.
- [`queue.json` grande] → ~3.500 itens de 7 repositórios, poucas centenas de KB; aceitável para o site.
