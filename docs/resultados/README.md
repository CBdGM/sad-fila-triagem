# Resultados

Relatórios gerados a partir do branch `data` (gabarito `gab-1`, Jev `jev-1.14.0` com as perguntas `q1`).
Métrica principal: AUC de "fechada sem ação" no teste temporal (70% das issues mais antigas de cada repositório
para treino, 30% mais recentes para teste). 0,5 = acaso, 1,0 = perfeito.

| Relatório | O que responde | Resultado principal |
|---|---|---|
| Fase 0 (seção "Resultado da Fase 0" no [README](../../README.md)) | Os repositórios têm gabarito utilizável? | VS Code 68%, TypeScript 48% e Godot 39% de "sem ação": passam no portão (≥ 15%) |
| [baselines-2026-11-24.md](baselines-2026-11-24.md) | O Jev supera métodos simples? | Jev + calibrador 0,78 · heurística 0,70 · TF-IDF 0,83 (3 repositórios juntos) |
| [experimento-q2-2026-11-28.md](experimento-q2-2026-11-28.md) | Perguntas ajustadas melhoram o Jev? | Não: 0,707 contra 0,718 da q1; manter a q1 |
| [experimento-configs-2026-11-28.md](experimento-configs-2026-11-28.md) | O que mais entra no calibrador? Um por repositório ou global? | Jev + TF-IDF + sinais do texto: 0,88 VS Code, 0,73 TypeScript, 0,80 Godot; melhor um calibrador por repositório |

Para gerar de novo: `python -m baselines`, `python -m experimentos.q2` e `python -m experimentos.configs`
(veja o cabeçalho de cada módulo). Os experimentos não mudam o job nem os arquivos do branch `data`.
