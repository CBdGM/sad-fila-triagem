## Context

A auditoria manual de 24/11 rodou estas checagens à mão e achou os dados íntegros. As que dependem de API (comparar contagens com a busca do GitHub, perguntar de novo ao Jev) ficam fora do job diário: a busca tem limite baixo e o Jev custa tokens.

## Decisions

**Dois níveis.** Erro = dado corrompido, que não pode chegar ao site. Atenção = dado parado ou crescendo, que alguém precisa olhar mas não invalida a fila. Os dois deixam o job vermelho, para o e-mail do GitHub chegar; só erro bloqueia a publicação.

**Limites, ajustáveis por opção:**
- última coleta: 36 horas (o job é diário; folga para atraso do agendamento do Actions);
- aberta sem previsão: 4 dias desde `first_seen_at` (com até 200 avaliações por repositório por dia, ~500 abertas novas são cobertas em 3 dias);
- tamanho do branch: 150 MB (a proposta falava em dezenas de MB; hoje são ~60).

**Fechadas sem desfecho comparam `number` + `closed_at`**, como o passo de desfechos: uma issue reaberta e fechada de novo precisa de desfecho novo.

**Job separado no workflow** (`auditar`, depois de `diario`, antes de `publicar`), lendo o branch `data` já commitado. Assim ele audita exatamente o que foi gravado, mesmo quando um passo do `diario` falhou no meio. O resultado vai para o `publicar` por uma saída do job (`corrupted`).

## Risks / Trade-offs

- [Atenção recorrente enquanto há backlog do Jev] → o limite de 4 dias cobre o ritmo atual; se o grupo aumentar os repositórios ou baixar o teto, o limite muda pela opção.
- [Validar todas as linhas todo dia fica lento] → hoje são ~50 mil linhas em segundos; se crescer muito, validar só as linhas novas desde o último commit.
