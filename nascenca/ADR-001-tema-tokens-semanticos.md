# ADR-001 — Tokens semânticos de tema desde o commit 1

## Status

Aceito. Extraído do ciclo Modo Claro do app do ciclo 2026 (T0→T2), onde a AUSÊNCIA desta
decisão custou a remediação de **6.606 cores hardcoded** em três fases auditadas. No dia 0
a baseline é ZERO de graça.

## Contexto

Todo app que nasce com cor direta no JSX (`bg-zinc-900`, `#123456`, `text-white`) está
decidindo, silenciosamente, que terá UM tema para sempre. Quando o segundo tema chega
(claro/escuro, white-label, acessibilidade), cada literal vira dívida: no app do ciclo 2026 foram
6.606, migradas por lotes com auditoria adversarial ao longo de semanas. Além disso, cor
escolhida no olho reprova contraste com frequência — um CTA a 2.94:1 passou por aprovação
visual e só caiu num validador computado (METODO §5.5).

## Decisão

1. **Nunca cor hardcoded em `.tsx`/`.ts`.** Sem paleta Tailwind solta, sem hex, sem
   rgb()/rgba() literal, sem hsl() cru, sem `text-white/black`. Só tokens semânticos.
2. **Tokens semânticos em HSL cru** em `globals.css` — `:root` = tema default,
   `.light` (ou `.dark`) = alternativo. Valor sem `hsl()` (`--background: 0 0% 5%;`) para
   compor alpha via `hsl(var(--token)/alfa)`. Nome diz FUNÇÃO, nunca cor.
3. **Guard de paleta com baseline ZERO no CI desde o commit 1** — o verificador de paleta
   de `guards/`, exit 1 em qualquer violação. Escape hatch justificado, com motivo
   escrito. Allowlist curta, cada entrada com motivo.
4. **Validador de contraste computado no CI** — o verificador de contraste
   (mesma pasta): valida WCAG 2.1 dos pares texto/fundo declarados
   nos 2 temas — texto ≥4.5:1, UI/hint/focus-ring ≥3:1, exit 1. A paleta é ajustada até o
   validador passar, nunca aprovada só no olho.

### Tabela de tokens mínima (copie e preencha)

| Grupo | Tokens | Regra |
|---|---|---|
| Fundo | `--background` · `--surface-1` · `--surface-2` · `--surface-overlay` | 3 superfícies bastam; não crie a 4ª sem ADR |
| Texto | `--foreground` · `--foreground-strong` · `--dim` · `--faint` | corpo / KPI-heading / secundário / hint (faint é tier UI 3:1) |
| Marca | `--primary` · `--primary-foreground` · `--primary-text` | `--primary-text` é a ÚNICA variante válida como texto; `--primary` só ícone/borda/superfície |
| Borda | `--border` · `--border-strong` · `--ring` | ring é o indicador de foco — gate 3:1 obrigatório |
| Estados | `--danger` · `--success` · `--warning` · `--info` (+ `--*-foreground` de cada) | par sólido + texto-sobre-superfície por estado |
| On-tokens | `--on-cta` · `--on-state` · `--on-success` (+ `--primary-foreground`) | texto sobre fundo SÓLIDO; um por fundo, par validado; podem INVERTER entre temas |
| Elevação | `--shadow-elevation-1` · `--shadow-elevation-2` | sombra é token também, senão `shadow-[rgba(...)]` vira dívida |

Pares obrigatórios no validador: cada texto × cada superfície; cada on-token × seu fundo
sólido; ring × background.

## Consequências

Positivas:
- Segundo tema custa horas (um bloco `.light` calibrado pelo validador), não semanas de
  migração — e white-label vira troca de valores, não de código.
- Contraste é gate de CI, não opinião: o par ilegível não entra no repo.
- A dívida nunca nasce: baseline zero + guard-catraca desde o primeiro PR.

Negativas / custos assumidos:
- Disciplina constante: todo dev aprende os nomes dos tokens (a tabela acima é o
  onboarding) e o guard recusa o atalho `bg-zinc-900`.
- O guard tem limitações declaradas no próprio cabeçalho — onde
  ele não alcança, vale screenshot nos 2 temas; a varredura visual com amostrador de
  contraste no app real (eixo tema da remediação, §4) cobre o resto.
- Exceções legítimas vivem em allowlist justificada — que só pode encolher.
