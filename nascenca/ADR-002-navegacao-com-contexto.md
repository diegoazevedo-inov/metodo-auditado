# ADR-002 — Navegação com contexto desde a primeira tela

**Status:** aceito (modelo de nascença — adotar ANTES da primeira tela)
**Origem:** ciclo real de remediação do app do ciclo 2026 (2026-07-16) — 93% dos "Voltar"
hardcoded, filtros em `useState`, zero deep-link; ver
[remediacao/20-eixo-fluxos.md](../remediacao/20-eixo-fluxos.md).

## Contexto

Em app de gestão, o fluxo dominante é serial: filtrar uma lista → abrir um detalhe →
agir → voltar → próximo item. Se "voltar" é um `router.push` fixo para a raiz do módulo
e o filtro vive em `useState`, cada volta zera o recorte. No app do ciclo 2026 isso virou dor
nomeada ("liquidar dois anos de parcelas refazendo o filtro a cada uma") e custou um
ciclo inteiro de remediação: auditoria medida, 4 fases, os botões Voltar migrados, 7 gaps de
ida-sem-volta, spec nova. **No dia 0, o mesmo padrão custa zero.**

## Decisão

Desde a primeira tela, sem exceção:

1. **Voltar SEMPRE via componente com fallback** (botão Voltar sobre um hook de retorno),
   com precedência fixa:
   `?returnTo=` validado → `router.back()` se há passo anterior interno nesta aba
   (trilha em `sessionStorage`) → `fallback` declarado. `router.push('/modulo')` cru em
   botão de voltar é proibido; grep de guard recusa.
2. **Filtro e aba SEMPRE na URL.** Abas via hook de aba na URL (`router.replace` com
   `{ scroll: false }`; aba padrão sai da URL; troca lê `window.location.search` para não
   pisar em params de outros donos). Filtros: hidratam do `useSearchParams()` no
   initializer e espelham de volta com `replace` + debounce; `setPage(1)` em toda troca
   de filtro; nunca `push` (histórico não é log de teclas).
3. **`returnTo` SEMPRE sanitizado** — recusar todo redirecionamento para fora do
   domínio: só path relativo interno das áreas permitidas; recusa URL absoluta, `//host`,
   `/\`, backslash/control chars e esquema embutido (`/javascript:`); valida também na
   MONTAGEM do link, não só no consumo.
4. **Toda lista filtrável é linkável**: os params que a tela grava ela lê. Ação que gera
   entidade em outro módulo entrega o link filtrado de volta (nada de "ida sem volta").
5. **Spec de navegação-retorno entra junto com a segunda tela** (o primeiro par
   lista→detalhe): filtro sobrevive ao voltar; deep-link hidrata; deep-link direto cai
   no fallback (aba nova); `returnTo` externo é ignorado. Clique-que-navega sempre
   `Promise.all([page.waitForURL(...), locator.click()])` — nunca `click` +
   `toHaveURL` de 5s, que quebra sob seed denso.

## Consequências

- **Baixas em série sem perder contexto**: o fluxo dominante (agir item a item sobre um
  recorte) nunca refaz filtro nem paginação — a produtividade do usuário não degrada com
  o tamanho do histórico.
- **Deep-link de graça**: F5, link compartilhado, atalho cross-module e "ver a fatura
  gerada" funcionam sem feature nova, porque a URL é a fonte de verdade do recorte.
- **Zero retrabalho de auditoria futura**: não existe estoque de "Voltar" hardcoded a
  migrar nem open-redirect a caçar — a baseline do guard nasce em ZERO e só pode subir
  com alarme (METODO §3, guard-catraca).
- **Custo aceito**: 3 utilitários (sanitizador + trilha, hook de retorno, hook de aba) e
  a disciplina de nunca escrever o atalho cru. Horas no dia 0; a
  alternativa, no app do ciclo 2026, custou um ciclo de remediação completo.
