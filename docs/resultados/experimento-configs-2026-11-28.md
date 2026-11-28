# Experimento: configurações do calibrador (2026-11-28)

Gerado por `python -m experimentos.configs`, sem chamar o Jev. Mesmos dados (backfill `q1`, gabarito `gab-1`), rótulo (positivo = sem ação), corte temporal por repositório (70% mais antigas = treino) e métricas dos baselines. Todo calibrador é uma regressão logística padronizada; a nota do TF-IDF entra como variável (empilhamento), calculada fora da amostra no treino.

## microsoft/vscode

Teste: 3123 issues, sem ação: 55%.

| Configuração (calibrador por repositório) | AUC [IC 95%] | Precisão média | Brier |
|---|---|---|---|
| Jev sozinho (referência) | 0.809 [0.794–0.824] | 0.857 | 0.206 |
| TF-IDF sozinho (referência) | 0.857 [0.844–0.870] | 0.899 | 0.163 |
| 1. Jev + quem escreveu | 0.857 [0.843–0.869] | 0.895 | 0.171 |
| 2. Jev + TF-IDF juntos | 0.868 [0.855–0.880] | 0.909 | 0.155 |
| 4. Jev + sinais do texto | 0.818 [0.803–0.832] | 0.866 | 0.201 |
| Tudo junto (Jev + autor + texto + TF-IDF) | 0.877 [0.865–0.889] | 0.916 | 0.146 |

AUC só com autores de fora da equipe: Jev sozinho 0.835 · TF-IDF sozinho 0.872 · 1. Jev + quem escreveu 0.839 · 2. Jev + TF-IDF juntos 0.888 · 4. Jev + sinais do texto 0.836 · Tudo junto 0.887.

**3. Por repositório × global** (global = um calibrador para os 3, com o repositório como variável):

| Configuração | Por repositório | Global |
|---|---|---|
| Jev sozinho (referência) | 0.809 | 0.809 |
| Tudo junto (Jev + autor + texto + TF-IDF) | 0.877 | 0.880 |

## microsoft/TypeScript

Teste: 140 issues, sem ação: 36%.

| Configuração (calibrador por repositório) | AUC [IC 95%] | Precisão média | Brier |
|---|---|---|---|
| Jev sozinho (referência) | 0.581 [0.474–0.679] | 0.510 | 0.238 |
| TF-IDF sozinho (referência) | 0.677 [0.585–0.769] | 0.506 | 0.219 |
| 1. Jev + quem escreveu | 0.579 [0.472–0.677] | 0.512 | 0.238 |
| 2. Jev + TF-IDF juntos | 0.691 [0.595–0.785] | 0.586 | 0.217 |
| 4. Jev + sinais do texto | 0.645 [0.546–0.733] | 0.523 | 0.232 |
| Tudo junto (Jev + autor + texto + TF-IDF) | 0.727 [0.635–0.809] | 0.610 | 0.207 |

AUC só com autores de fora da equipe: Jev sozinho 0.581 · TF-IDF sozinho 0.677 · 1. Jev + quem escreveu 0.579 · 2. Jev + TF-IDF juntos 0.691 · 4. Jev + sinais do texto 0.645 · Tudo junto 0.727.

**3. Por repositório × global** (global = um calibrador para os 3, com o repositório como variável):

| Configuração | Por repositório | Global |
|---|---|---|
| Jev sozinho (referência) | 0.581 | 0.602 |
| Tudo junto (Jev + autor + texto + TF-IDF) | 0.727 | 0.622 |

## godotengine/godot

Teste: 473 issues, sem ação: 39%.

| Configuração (calibrador por repositório) | AUC [IC 95%] | Precisão média | Brier |
|---|---|---|---|
| Jev sozinho (referência) | 0.624 [0.568–0.676] | 0.591 | 0.226 |
| TF-IDF sozinho (referência) | 0.750 [0.707–0.794] | 0.664 | 0.210 |
| 1. Jev + quem escreveu | 0.666 [0.616–0.717] | 0.615 | 0.218 |
| 2. Jev + TF-IDF juntos | 0.772 [0.726–0.816] | 0.692 | 0.205 |
| 4. Jev + sinais do texto | 0.697 [0.650–0.742] | 0.636 | 0.212 |
| Tudo junto (Jev + autor + texto + TF-IDF) | 0.801 [0.760–0.840] | 0.722 | 0.195 |

AUC só com autores de fora da equipe: Jev sozinho 0.629 · TF-IDF sozinho 0.748 · 1. Jev + quem escreveu 0.630 · 2. Jev + TF-IDF juntos 0.774 · 4. Jev + sinais do texto 0.699 · Tudo junto 0.781.

**3. Por repositório × global** (global = um calibrador para os 3, com o repositório como variável):

| Configuração | Por repositório | Global |
|---|---|---|
| Jev sozinho (referência) | 0.624 | 0.637 |
| Tudo junto (Jev + autor + texto + TF-IDF) | 0.801 | 0.755 |
## Conclusão

| AUC no teste | VS Code | TypeScript | Godot |
|---|---|---|---|
| Jev sozinho | 0,809 | 0,581 | 0,624 |
| TF-IDF sozinho | 0,857 | 0,677 | 0,750 |
| **Jev + TF-IDF juntos** | **0,868** | **0,691** | **0,772** |
| **Tudo junto** (Jev + autor + texto + TF-IDF) | **0,877** | **0,727** | **0,801** |

- **O Jev agrega algo que as palavras não têm.** Juntar as respostas do Jev com a nota do TF-IDF é melhor que cada um sozinho
  nos 3 repositórios (+0,01 a +0,02 de AUC sobre o TF-IDF), e também só com autores de fora (VS Code 0,888 contra 0,872).
  O ganho é pequeno e os intervalos se sobrepõem nos repositórios menores, mas a direção é a mesma em todos.
- **Melhor configuração: tudo junto, com calibrador por repositório.** É a melhor nos 3 (VS Code 0,877, TypeScript 0,727,
  Godot 0,801) e a de melhor calibração (Brier mais baixo).
- **"Quem escreveu" ajuda muito no VS Code (0,809 → 0,857), mas quase nada entre autores de fora (0,835 → 0,839).** Ou seja,
  ele separa issues da equipe das de fora; para a fila, que atende quem é de fora, o ganho real é pequeno.
- **Sinais simples do texto ajudam nos repositórios menores** (TypeScript 0,58 → 0,65; Godot 0,62 → 0,70) e pouco no VS Code.
- **3. Por repositório × global:** com o Jev sozinho, o global ajuda os repositórios pequenos (TypeScript 0,58 → 0,60,
  Godot 0,62 → 0,64), porque aproveita mais dados. Com o texto (TF-IDF), o calibrador por repositório é bem melhor
  (TypeScript 0,73 contra 0,62; Godot 0,80 contra 0,76): o vocabulário de cada projeto é próprio e o VS Code domina o global.
  Recomendação: **um calibrador por repositório** quando entra texto.

Para o Back: o calibrador da proposta (só as respostas do Jev) fica bem abaixo do que os dados permitem. Acrescentar a nota
de um TF-IDF e sinais simples do texto como variáveis é barato (sem custo de Jev) e dá o maior ganho observado.

## Limitações

- O `C` do TF-IDF é escolhido no mesmo treino em que se calcula a nota fora da amostra, o que deixa o empilhamento levemente otimista.
- TypeScript tem 140 issues no teste: intervalos largos.
- Um teste temporal só; o teste entre repositórios e o prospectivo da proposta continuam com o Back.
