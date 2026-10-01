---
name: auditar-tema
description: Auditoria MEDIDA do eixo tema claro/escuro — conta cores hardcoded por espécie e arquivo, avalia tokens/contraste existentes e devolve o esqueleto do PLAN T0→T2. Não corrige nada. Use quando o projeto tem (ou vai ganhar) mais de um tema, ou quando há suspeita de cor hardcoded em massa.
---

Você vai executar a auditoria medida do eixo TEMA no projeto atual. NÃO corrija nada —
meça, rankeie e proponha. Método completo: `remediacao/10-eixo-tema.md` (se o kit
estiver no repo) ou peça ao usuário o caminho do kit.

## 1. Medir (adapte os diretórios ao projeto)

Rode o verificador de paleta do repositório sobre o código de UI do projeto. O
`guards/guards.toml` vem ajustado para a aplicação de exemplo: **copie o arquivo para fora de
`guards/`** e ajuste na cópia `[projeto].raiz_ui` (caminho absoluto funciona),
`[paleta].cores_marca`, `[paleta].tokens_semanticos` e `[paleta.isentos]` (a allowlist de
exemplo gera aviso de entrada sem uso). Depois, na pasta dos verificadores:

```bash
cd guards/
python3 -m uiguards.palette --config <caminho-da-copia>/guards.toml
```

Com violação o código de saída é `1` — na auditoria é o esperado, não erro. A saída já vem
por espécie, com a contagem no cabeçalho de cada grupo (`-- N ocorrencia(s)`) e `TOTAL` no
fim. Conte pelo nome que o verificador imprime: hex literal (`hex-literal`);
`rgb()`/`rgba()`/`hsl()` fora de `var(` (`rgb-literal` + `hsl-literal`; `cor-funcional-moderna`
para `oklch()`, `lab()` etc.); paleta crua do utilitário de CSS (`escala-framework`);
`white`/`black` direto (`cor-absoluta`); cor de marca como texto (`marca-como-texto`).

As variantes de superfície **não vêm do verificador**: é inspeção manual dos tons de card. O
ranking por arquivo **não vem pronto** (a saída agrupa por espécie); esta linha monta o top 15
(= o ranking de lotes) e soma o mesmo `TOTAL`:

```bash
python3 -m uiguards.palette --config <caminho-da-copia>/guards.toml \
  | grep -oE '^    [^ ^][^:]*:[0-9]+:' | cut -d: -f1 | sed 's/^ *//' \
  | sort | uniq -c | sort -rn | head -15
```

Inspecione também: existe CSS global com tokens? (`:root`/tema alternativo) Existe
provider de tema? Specs de tema? Guard de paleta?

## 2. Reportar (formato obrigatório)

- Tabela: espécie de violação × contagem; top ofensores.
- Estado das fundações: tokens (sim/não), provider (sim/não), guard (sim/não).
- Esqueleto do PLAN: **T0** tokens+validador de contraste+provider (manual/SO/agendado se
  o dono quiser)+paleta piloto com GATE VISUAL DO DONO · **T1** migração em massa por
  lotes rankeados atrás de feature-flag opt-out · **T2** specs permanentes (persistência,
  varredura visual nos 2 temas, amostrador de contraste no app real) + guard no CI.
- Perguntas ao dono (não decida por ele): default de tema? paleta-alvo? kill-switch?

## 3. Nunca

Não invente números; não corrija "de passagem"; não proponha migração sem gate visual.
