# ADR-003 — Layout responsivo por gabarito, varredura-como-spec e guard com baseline ZERO

**Status**: modelo de nascença (adotar ANTES da primeira tela)
**Origem**: ciclo H0→H2 do app do ciclo 2026 — 60 rotas quebradas medidas → 0 em 4 lotes.

## Contexto

Sem um page-shell compartilhado, cada tela reimplementa header, espaçamentos e tabelas à mão — e a
dívida responsiva nasce silenciosa: no app do ciclo 2026, 40% das páginas não tinham NENHUMA classe
responsiva, containers `overflow-hidden` amputavam colunas de 5 tabelas (até 450px inalcançáveis) e o
shell `overflow-hidden` cegava qualquer métrica de página. Remediar custou um ciclo inteiro
(H0→H2), 4 lotes auditados e semanas; a dívida de guard (86) levou o ciclo todo para descer a 67.
**No dia 0, a baseline é ZERO de graça.**

## Decisão

Três peças obrigatórias desde o primeiro commit de UI:

1. **Gabarito de layout (page-shell)** — toda tela de módulo abre com `<PageShell>`; toda
   `<table>` vive em `<ScrollTable>`; texto livre trunca via `<TextCell>` (`truncate` +
   `title`); **número nunca trunca** (`break-words`/grid); padding de página vem do LAYOUT, nunca
   da página. Regras completas no `PADROES-layout.md` do projeto.
2. **Varredura-como-spec** — detector de estouro por ELEMENTO aplicado pela varredura à matriz
   de viewports (360/390/768/1440), com o consolidador assinando o resultado; prova canônica =
   **assinatura sha256 do conjunto de defeitos** — que aqui nasce e PERMANECE VAZIA. Usar o detector, a
   varredura e o consolidador de `guards/`.
3. **Catraca de layout com baseline ZERO** — as 4 regras do gabarito que ela cobra rodam em
   modo **estrito desde o dia 0**: sem
   dívida legada não há razão para catraca — qualquer violação é exit 1 no CI/pre-commit. Escape
   hatch só com justificativa escrita.

## Anatomia mínima do gabarito (pronta para copiar)

```tsx
// page-shell.tsx — o que ele TEM de garantir (cada item fecha uma causa medida)
export function PageShell({ titulo, acoes, children }: Props) {
  return (
    <div className="min-w-0 space-y-8">                {/* min-w-0 na raiz: filho de flex/grid se recusa a encolher */}
      <header className="flex min-w-0 flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <h1 className="min-w-0 truncate text-2xl" title={titulo}>{titulo}</h1>
        <div className="flex min-w-0 flex-wrap gap-2">{acoes}</div>  {/* min-w-0, NÃO shrink-0: botões quebram */}
      </header>
      {children}                                       {/* SEM padding próprio: o layout já dá p-4 md:p-10 */}
    </div>
  );
}

// scroll-table.tsx — rolagem honesta + contenção de medição
export function ScrollTable({ children }: Props) {
  return (
    <div className="overflow-x-auto [contain:paint]">  {/* sem contain:paint a tabela infla o scrollWidth dos ANCESTRAIS */}
      <table className="w-full">{children}</table>     {/* fonte é do CHAMADOR — não injetar text-sm */}
    </div>
  );
}
// ⚠️ contain:paint recorta absolute/fixed internos: overlay em linha de tabela = PORTAL, nunca absolute na célula.

// text-cell.tsx — truncar só texto LIVRE, sempre legível por inteiro
export function TextCell({ titulo, children }: Props) {
  return <td className="min-w-0 max-w-[16rem] truncate px-4 py-3" title={titulo}>{children}</td>;
}
```

E no layout do shell, a marcação que os verificadores pedem para separar defeito do shell de
defeito de página (ver a documentação deles).

## Consequências

- **A classe de dívida não nasce.** As violações do gabarito são recusadas no primeiro commit — não existem "86 violações legítimas" para
  administrar, nem catraca, nem 4 lotes de migração.
- A varredura roda desde a 1ª tela com assinatura vazia; a PRIMEIRA linha que aparecer é regressão
  nomeada, não arqueologia.
- Custo: configurar 3 verificadores + escrever 3 componentes (~1 dia). A alternativa medida custou um ciclo
  de remediação inteiro com 6 rodadas de auditoria.
- Riscos aceitos: o detector não vê sobreposição, estouro vertical nem compressão ilegível (regra
  de densidade ≥11px cobre a última); `title` não existe em touch (prever tap-para-expandir);
  telas medidas com banco vazio são PISO — seeds densos continuam necessários para medição honesta.
