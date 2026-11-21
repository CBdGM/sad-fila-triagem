# sad-fila-triagem

SAD v3: fila priorizada de triagem de issues com o Jev. Projeto da disciplina IF1006
(Transformação Digital com IA, CIn-UFPE).

Um job diário lê as issues de repositórios públicos do GitHub (só leitura), o Jev responde
perguntas fechadas sobre cada uma, um calibrador treinado no histórico estima a chance de a issue
ser fechada sem ação e um site estático mostra a fila em três faixas: atenção primeiro, revisão
humana e provavelmente sem ação, sempre com o motivo.

A PoC que deu origem a este projeto está em
[CBdGM/sad-poc-decisao](https://github.com/CBdGM/sad-poc-decisao) (branch `app-triagem`).

## Estrutura

```
contracts/      formato de cada arquivo trocado entre as equipes (JSON Schema + exemplos)
openspec/       requisitos e mudanças no formato do OpenSpec
  specs/        o sistema como está (fonte da verdade)
  changes/      mudanças em andamento, uma pasta por mudança
```

Ainda por vir, conforme as fases: coletor e job (`.github/workflows/`), calibrador e avaliação,
site da fila, e o branch `data` com o histórico.

## Como trabalhamos (OpenSpec)

Cada mudança grande começa como um change do OpenSpec, revisado pelo time antes do código:

1. No Claude Code, Cursor ou Copilot: `/openspec-propose <descrição>` gera `proposal.md`,
   `specs/`, `design.md` e `tasks.md` em `openspec/changes/<nome>/`.
2. O time revisa e ajusta o change (de preferência num PR).
3. `/openspec-apply-change` implementa seguindo o `tasks.md`.
4. Depois da revisão do código, `/openspec-archive-change` incorpora os requisitos em `openspec/specs/`.

Os comandos `/openspec-*` precisam do CLI. Sem instalar nada global:

```bash
npx @fission-ai/openspec@latest list
```

Para instalar global (Node 22.20 ou mais novo): `npm install -g @fission-ai/openspec@latest`.
O CLI coleta telemetria anônima por padrão; para desligar, `openspec config set telemetry.enabled false`
ou `export DO_NOT_TRACK=1`.

## Contratos

Veja [contracts/README.md](contracts/README.md). Para validar:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python contracts/validate.py
```

## Segredos

Nenhuma chave entra no código nem em commit. A chave do Jev (`TYPESAFE_API_KEY`) fica nos
*secrets* do GitHub Actions; localmente, num `.env` (já ignorado pelo `.gitignore`).
