# Eixo 1 — Tema claro/escuro (remediação)

Aplicação do [METODO.md](../METODO.md) ao eixo de tema. No app do ciclo 2026: **6.606 cores
hardcoded → 0** em três fases (T0→T2), com dark default preservado e claro
opt-in. Este documento é a receita; os nomes de token citados são os REAIS do ciclo de
origem, e os verificadores estão em `guards/`.

---

## 1. Auditoria medida (a receita de 30 min)

Nada de opinião: meça, some, e o total vira a manchete do PLAN ("6.606 cores
hardcoded" foi a nossa). A medição é o verificador de paleta do repositório, rodado sobre todo o
código de UI do projeto.

O `guards/guards.toml` vem ajustado para a aplicação de exemplo. **Copie o arquivo para fora de
`guards/`** e ajuste na cópia `[projeto].raiz_ui` (caminho absoluto funciona),
`[paleta].cores_marca`, `[paleta].tokens_semanticos` e `[paleta.isentos]` (a allowlist de
exemplo gera aviso de entrada sem uso). Depois, na pasta dos verificadores:

```bash
cd guards/
python3 -m uiguards.palette --config <caminho-da-copia>/guards.toml
```

Com violação o código de saída é `1` — na auditoria isso é o esperado, não erro. A saída agrupa
por espécie, com a contagem no cabeçalho de cada grupo (`-- N ocorrencia(s)`) e o `TOTAL` no fim.

O que contar no resultado (entre parênteses, o nome que o verificador imprime):

1. hex literal em `.tsx`/`.ts` (`hex-literal`);
2. `rgb()`/`rgba()`/`hsl()` fora de `var(` (`rgb-literal` + `hsl-literal`; e
   `cor-funcional-moderna` para `oklch()`, `lab()` etc.);
3. paleta crua do utilitário de CSS — tons neutros + cores de estado, a massa da dívida
   (`escala-framework`);
4. `white`/`black` direto — quebram um dos dois temas (`cor-absoluta`);
5. **variantes de superfície** — quantos "tons de card" diferentes existem (no app do ciclo 2026
   eram 8+ variantes; viraram 3 tokens `surface-*`). **Não vem do verificador:** é inspeção
   manual dos tons de card;
6. **contrastes suspeitos** — cor de marca usada como texto, no claro reprova
   (`marca-como-texto`);
7. **ranking de ataque** — os arquivos com mais violações primeiro. **Não vem pronto** (a saída
   agrupa por espécie); esta linha monta o ranking e soma o mesmo `TOTAL`:

   ```bash
   python3 -m uiguards.palette --config <caminho-da-copia>/guards.toml \
     | grep -oE '^    [^ ^][^:]*:[0-9]+:' | cut -d: -f1 | sed 's/^ *//' \
     | sort | uniq -c | sort -rn | head -15
   ```

Some 1–4 e 6 = **o placar**. O item 5 diz quantos tokens de superfície você vai precisar
(spoiler: 3 bastam). O item 7 define a ordem dos lotes da T1. Guarde o comando: a mesma
medição vira guard permanente na T2 (o verificador de paleta cobre também as combinações que
uma contagem simples não alcança).

## 2. Fases T0→T2 (entrega e gate de cada uma)

### T0 — Fundação: tokens + validador + 3 modos + piloto COM GATE VISUAL DO DONO

Entrega:
- **Bloco de tokens** em `globals.css`: `:root` = tema original (default + fallback SSR),
  `.light` = tema novo. Estrutura mínima na §3. Valores do claro partem de uma tabela
  proposta e são AJUSTADOS ATÉ O VALIDADOR PASSAR — não o contrário.
- **Validador de contraste computado** (o verificador de contraste, em `guards/`):
  reprova (exit 1) qualquer par texto/fundo declarado abaixo do mínimo WCAG 2.1 nos 2 temas
  (texto ≥4.5:1, UI/hint/ring ≥3:1).
  Nasce JUNTO com os tokens, não depois — é ele que calibra a paleta.
- **Provider único de modo** (sobre next-themes): `manual` | `system` |
  `schedule` (claro 07:00–18:00, recalcula a cada 60s + foco da aba; override do toggle
  vale até a próxima fronteira). Provider, não hook por instância — o loop do agendado e o
  estado de override existem UMA vez; `storage` listener sincroniza multi-aba.
- **Piloto**: 2 telas de verdade (1 boa + 1 péssima) migradas para tokens, screenshot nos
  2 temas.

**Gate: aprovação VISUAL do dono sobre o piloto.** Paleta é decisão de produto — nenhuma
migração em massa antes do "aprovo o tema claro". Registrada com data no PLAN.

### T1 — Migração em massa por lotes

- Lotes na ordem do ranking da auditoria (T1-a/b/c no app do ciclo 2026), cada lote com HANDOFF e
  auditoria adversarial antes do próximo.
- Substituição é mecânica MAS não confiável cega: **subagentes deixam órfãos** — classes
  malformadas (`bg-x/40/[0.03]`, duplo modificador de opacidade que o Tailwind nem gera),
  hex esquecido em prop, ternário com só uma branch migrada. **Depois de cada lote,
  re-rode a medição da §1** — o número do lote tem de chegar a zero medido, não relatado.
- **Feature-flag desde o 1º lote**: `<FLAG_TEMA>` (variável pública, inlinada no build). Começa
  opt-in; quando a T1 encerra vira **opt-OUT** (ausente = disponível; `false` =
  kill-switch que força o tema original). Isso permite MERGE contínuo na main durante a
  migração — sem branch de longa vida.
- Pares que a contagem não vê nascem aqui e viram regra do guard: fundo sólido + texto errado,
  cor de marca como texto.

**Gate: placar do lote em zero (medição da §1) + validador verde + screenshots dos 2 temas.**

### T2 — Specs permanentes

- **Spec de comportamento** de tema: persistência do toggle após reload;
  deep-link abre no tema salvo; **sem flash** (asserção em `domcontentloaded` — o script
  inline do next-themes já rodou, o React ainda não hidratou: exatamente a janela do
  flash); modo agendado com **mock de relógio** (`page.clock.install` + `fastForward`
  cruzando 18:00 e 07:00 — fronteira EXECUTADA, não analisada); override que expira na
  fronteira; kill-switch (execução dedicada: `<FLAG_TEMA>=false npm run dev` + a spec de tema rodada no
  modo desligado — os demais testes pulam com skip declarado, "falha por motivo certo vira
  ruído").
- **Varredura visual** (spec própria): TODAS as rotas nos 2 temas
  (todas as áreas, inclusive as autenticadas com seed denso, + modais principais),
  screenshot fullPage por rota — artefato para revisão humana.
- **Amostrador de contraste no app REAL** (mesma spec): mede a razão dos textos
  RENDERIZADOS, não só dos tokens — é ele que acha o par que o guard estrutural não vê
  (classe herdada, cn() dinâmico). Relatório JSON por tema com toda amostra abaixo do
  mínimo.

**Gate: 0 falhas de contraste na amostragem real + guard limpo + suite verde.**

## 3. Decisões de design que valem ouro (do app do ciclo 2026)

- **Tokens SEMÂNTICOS em HSL cru** (`--background: 0 0% 5%;` — sem `hsl()` no valor, o
  utilitário compõe `hsl(var(--token)/alfa)`). Nome diz FUNÇÃO, nunca cor: `surface-1/2/
  overlay`, `foreground`/`foreground-strong`/`dim`/`faint`, `border`/`border-strong`,
  `danger`/`success`/`warning`/`info`/`info-2`. **Nunca cor direta em .tsx/.ts.**
- **Cor de marca como texto reprova**: a cor da marca sobre o fundo claro dá **2.36:1** →
  variante SÓ-TEXTO `--primary-text` (um tom mais escuro, `<valor>`, no claro; no dark é
  idêntica à cor da marca). A cor da marca continua viva em ícone/borda/superfície
  (`text-primary` só em ícone). O `--ring` de foco também usa o tom escuro no claro (a cor da
  marca reprova o gate 3:1 de UI).
- **on-tokens para texto sobre fundo sólido**, um por fundo (`--on-success`, `--on-state`,
  `--on-cta`, mais o `--primary-foreground` da marca), cada par VALIDADO no validador. Não é
  frescura: o on-token INVERTE entre temas (`--on-cta` é escuro no dark e branco no claro) —
  nenhum texto fixo serviria os dois.
- **Flag kill-switch opt-OUT inlinada no build**: ausente =
  claro disponível; `false` = toggle some e o provider força o tema original para todos.
  Rollback de emergência sem reverter commit.
- **O default do app continua o tema original** (dark, no app do ciclo 2026). A flag define se o
  usuário PODE optar, nunca troca o default — zero surpresa para a base instalada.
- **Sombras são tokens também**: `--shadow-elevation-1/2` (glow no dark, sombra suave no
  claro) — senão todo `shadow-[...rgba(...)]` vira dívida nova.

## 4. Legado permanente (o que fica impedindo a dívida de voltar)

- **Palette guard** (o verificador de paleta, em `guards/`): recusa cor fora dos
  tokens, par fundo/texto errado e classe inválida. **Limitações DECLARADAS no cabeçalho do
  verificador**; o que ele não cobre se confere por screenshot nos 2 temas.
- **Validador WCAG computado** (o verificador de contraste): texto ≥4.5, UI ≥3, nos 2 temas,
  exit 1. Roda com o guard de paleta num check único — pré-commit de qualquer UI.
- **Amostrador no app real** (na varredura T2): large-text WCAG correto — mínimo 3:1 só
  para ≥24px, ou **≥18.66px SOMENTE em bold ≥700** (errar isso perdoa heading fino
  ilegível). **Cuidado: Tailwind v4 emite cores com alpha como `oklab(...)`** — parser
  ingênuo de "primeiros números da string" lê oklab como RGB (no dark o erro se esconde,
  no claro inventa centenas de falhas). Converta pelo PRÓPRIO browser (canvas 1×1 +
  `fillStyle` + `getImageData`) e componha alpha de fora para dentro; amostre só elemento
  com nó de TEXTO direto (cor herdada de contêiner mediu 2.94 num botão cujo real era
  5.97).
- **Escape hatch comentado**: marcador com motivo escrito (formato: ver os verificadores).
  Allowlist de arquivos CURTA, cada entrada com motivo escrito.

## 5. Armadilhas pagas (não repita)

- **Aprovação visual deixou passar CTA a 2.94:1.** O par `bg-cta text-primary-foreground`
  foi aprovado no olho e só caiu na amostragem real da T2. Por isso o guard
  exige o on-token EXATO do fundo. **Gate computado > olho** — o olho aprova estética, o número
  aprova contraste.
- **`text-primary` em texto passa no claro? NÃO — 2.36:1.** Checagem estrutural não pega
  todos os casos: o par errado só aparece por inteiro na amostragem do app real.
- **Migração automática deixa classe que o Tailwind não gera** (`bg-x/40/[0.03]`): o CSS
  simplesmente não existe e o elemento fica transparente num tema só.
- **Testar o agendado sem mock de relógio é não testar**: a fronteira 18:00 do app do ciclo 2026
  ficou "verificada por análise" da T0 até a T2, quando `page.clock` executou de verdade.
