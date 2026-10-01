# Seções-modelo para o CLAUDE.md de um projeto novo

> Copie, preencha os `<>` e apague o que não usar. São as seções que, no projeto-origem,
> fizeram agentes de IA respeitarem o método sem supervisão — escritas como REGRA
> ABSOLUTA, com tabela de referência e comando de verificação, nunca como "boas práticas".

---

## 🎨 TEMA (claro/escuro) — REGRA ABSOLUTA

**NUNCA cor hardcoded em componente — só tokens semânticos.** O app tem <N> tema(s)
(<default> default) e todo hex/rgb/`<paleta>-*`/text-white/black quebra um deles.

| Uso | Token |
|---|---|
| Fundo página/card/modal | `bg-background` · `bg-surface-1` · `bg-surface-2` |
| Texto corpo/heading/secundário | `text-foreground` · `text-foreground-strong` · `text-dim` |
| Texto de marca sobre claro | `<variante-texto-da-marca>` (a cor-marca crua pode reprovar contraste como texto — valide) |
| Bordas | `border-border` · `border-border-strong` |
| Estados | `text-danger-foreground` · `text-success-foreground` · … |
| Texto sobre fundo SÓLIDO | par on-token validado (`bg-cta`→`text-on-cta` …) |

Tokens definidos em `<caminho do CSS global>`. **Antes de commitar UI:**
`<check de tema>` (verificador de paleta + verificador de contraste WCAG nos <N> temas).
Escape hatch: marcador com motivo escrito (formato dos verificadores).

---

## 📐 HARMONIA / RESPONSIVIDADE — REGRA ABSOLUTA

Toda rota sobrevive a **<matriz: ex. 360/390/768/1440>px** sem estouro horizontal.

- Tela de módulo abre com `<PageShell>`; `<table>` SEMPRE dentro de `<ScrollTable>`;
  texto livre longo com `<TextCell>` (trunca + title) — os componentes do gabarito do ADR-003. `min-w-0` em todo filho de
  flex/grid com texto que cresce. **Nunca truncar número** — `break-words`.
- Padding de página vem do LAYOUT — não repetir na página.
- **Antes de commitar UI:** `<check de harmonia>` (catraca de layout, baseline
  em `<caminho>`; reduziu dívida → re-fixar a baseline no mesmo commit).
- Varredura responsiva é SPEC (`<caminho da spec>`): prova canônica = assinatura sha256
  VAZIA; UMA varredura por vez; seeds densos (`<scripts de seed>`).

---

## 🧭 NAVEGAÇÃO — REGRA ABSOLUTA

- "Voltar" usa `<componente-voltar fallback=…>` — NUNCA push fixo para a raiz do módulo.
- Filtros e abas vivem na URL (`<hook-de-aba>` / `router.replace` sem scroll reset).
- `?returnTo=` SEMPRE via `<sanitizador-de-returnTo>` (anti open-redirect: só paths
  relativos das áreas permitidas).

---

## 📱 PWA (se aplicável)

- Política de cache POR TIPO em `<next.config>`: dado vivo autenticado (`/api`, `/uploads`)
  = **NetworkOnly** (Workbox IGNORA Cache-Control private); estáticos CacheFirst;
  navegação NetworkFirst → `/offline`. Offline = só-leitura salvo ADR contrário.
- SW só existe em build de produção → testar em porta isolada; specs desregistram ao
  final; prova = `active.state==='activated'` + `controller`.
- Update por toast do design system — **NUNCA `window.confirm`**.

---

## Disciplina de ambiente (para agentes e humanos)

- Servidores de pé ANTES de qualquer suíte. Exit code real (`PIPESTATUS[0]`).
- NUNCA build/generate com E2E rodando. UMA varredura por vez.
- Fixtures de documento/dados fiscais SEMPRE pelo gerador validado (`<helper>`).
