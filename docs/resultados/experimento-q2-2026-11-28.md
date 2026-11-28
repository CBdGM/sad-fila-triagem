# Experimento q2: perguntas ajustadas ao Jev (2026-11-28)

Gerado por `python -m experimentos.q2`. Não muda o job nem o branch `data`.

Amostra: 2067 issues fechadas (todo o TypeScript, até 800 de Godot e de VS Code, semente 42), com desfecho `no_action`/`action` (`gab-1`). Corte temporal dentro da amostra de cada repositório (70% mais antigas = treino). As respostas q1 são as do backfill; as q2 foram pedidas ao Jev (jev-1.14.0) para este experimento, ~2.6 milhões de tokens.

## O que mudou nas perguntas

- **É defeito?** passa a dizer que pedido de recurso, desempenho, dúvida e spam não são defeito.
- **É pedido de recurso?** (nova).
- **É spam ou texto sem sentido?** (nova).
- **Informação suficiente?** passa a valer também para pedidos (descrição clara do que se quer).
- **Dá para agir?**, **pergunta de uso?** e **severidade** iguais à q1.

## microsoft/vscode

Treino 560 · teste 240 · sem ação no teste: 56%

| Modelo | AUC [IC 95%] | Precisão média | Brier |
|---|---|---|---|
| Jev q1 bruto (1 − é defeito) | 0.653 [0.577–0.723] | 0.659 | — |
| Jev q2 bruto (1 − é defeito) | 0.548 [0.470–0.621] | 0.599 | — |
| Jev q1 + regressão | 0.862 [0.811–0.906] | 0.908 | 0.180 |
| Jev q2 + regressão | 0.850 [0.799–0.895] | 0.898 | 0.188 |
| TF-IDF + regressão (régua) | 0.865 [0.821–0.911] | 0.904 | 0.183 |

AUC de cada pergunta q2 sozinha no teste: is_defect 0.55, is_feature_request 0.33, is_spam 0.70, actionable 0.83, enough_info 0.77, usage_question 0.67.

## microsoft/TypeScript

Treino 327 · teste 140 · sem ação no teste: 36%

| Modelo | AUC [IC 95%] | Precisão média | Brier |
|---|---|---|---|
| Jev q1 bruto (1 − é defeito) | 0.618 [0.521–0.718] | 0.531 | — |
| Jev q2 bruto (1 − é defeito) | 0.641 [0.545–0.740] | 0.525 | — |
| Jev q1 + regressão | 0.581 [0.474–0.679] | 0.510 | 0.238 |
| Jev q2 + regressão | 0.550 [0.447–0.651] | 0.467 | 0.236 |
| TF-IDF + regressão (régua) | 0.677 [0.585–0.769] | 0.506 | 0.219 |

AUC de cada pergunta q2 sozinha no teste: is_defect 0.64, is_feature_request 0.61, is_spam 0.52, actionable 0.57, enough_info 0.51, usage_question 0.62.

## godotengine/godot

Treino 560 · teste 240 · sem ação no teste: 38%

| Modelo | AUC [IC 95%] | Precisão média | Brier |
|---|---|---|---|
| Jev q1 bruto (1 − é defeito) | 0.567 [0.486–0.646] | 0.569 | — |
| Jev q2 bruto (1 − é defeito) | 0.565 [0.490–0.638] | 0.517 | — |
| Jev q1 + regressão | 0.612 [0.533–0.689] | 0.568 | 0.224 |
| Jev q2 + regressão | 0.604 [0.521–0.682] | 0.563 | 0.225 |
| TF-IDF + regressão (régua) | 0.734 [0.666–0.802] | 0.665 | 0.200 |

AUC de cada pergunta q2 sozinha no teste: is_defect 0.57, is_feature_request 0.59, is_spam 0.61, actionable 0.60, enough_info 0.54, usage_question 0.61.

## Todos (3 repositórios)

Treino 1447 · teste 620 · sem ação no teste: 45%

| Modelo | AUC [IC 95%] | Precisão média | Brier |
|---|---|---|---|
| Jev q1 bruto (1 − é defeito) | 0.658 [0.614–0.698] | 0.609 | — |
| Jev q2 bruto (1 − é defeito) | 0.622 [0.577–0.663] | 0.560 | — |
| Jev q1 + regressão | 0.718 [0.676–0.759] | 0.746 | 0.204 |
| Jev q2 + regressão | 0.707 [0.665–0.749] | 0.728 | 0.207 |
| TF-IDF + regressão (régua) | 0.755 [0.715–0.793] | 0.754 | 0.196 |

AUC de cada pergunta q2 sozinha no teste: is_defect 0.62, is_feature_request 0.51, is_spam 0.67, actionable 0.71, enough_info 0.66, usage_question 0.67.

## Conclusão

**A q2 não melhora o Jev.** Com o calibrador simples por cima, a AUC ficou igual ou um pouco menor que a da q1 em todos os
repositórios (todos: 0,707 contra 0,718), e as diferenças estão dentro dos intervalos de confiança. Recomendação: **manter a q1**
e não mudar o contrato de previsões.

Por que a hipótese não se confirmou:

- **Pedido de recurso não é sinal de "sem ação".** A pergunta nova "é pedido de recurso?" sozinha deu AUC 0,33 no VS Code,
  ou seja, aponta para o lado contrário: lá, pedidos de recurso (muitos abertos pela própria equipe) costumam virar PR.
  Deixar "é defeito?" mais estrita, excluindo pedidos de recurso, piorou a resposta bruta (0,65 → 0,55).
- **O calibrador já absorvia a confusão.** O erro de "chamar pedido de recurso de defeito" que vimos na comparação às cegas
  não atrapalha a regressão, que aprende o peso de cada resposta. As respostas que mais separam são "dá para agir?"
  (0,83 sozinha no VS Code) e "informação suficiente?".
- **Spam ajuda um pouco sozinho** (0,70 no VS Code), mas pouco somado às outras respostas.

O que falta ao Jev, nos dados, parece ser **contexto**, não reformular as perguntas: o que o projeto aceita (a chamada B,
cartão de escopo, já prevista na proposta) e quem escreveu a issue (equipe ou não). Nesta amostra menor, o Jev q1 com
regressão empata com o TF-IDF no VS Code (0,862 × 0,865); a diferença aparece no Godot e no TypeScript.

## Limitações

- Amostra menor que a dos baselines (o TF-IDF também treina com menos dados aqui, então os números não são diretamente comparáveis com o relatório de baselines; a comparação justa é dentro desta tabela).
- O Jev não é totalmente determinístico (variação de até ~0,04 por resposta).
- TypeScript pequeno: intervalos largos.
