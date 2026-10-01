# Eixo 2 — Fluxos contínuos de UI-UX (remediação)

> Aplicação do [METODO.md](../METODO.md) ao eixo de navegação com contexto. Ciclo real
> (implementado, auditado e aprovado em 2026-07-16).

---

## 1. O sintoma que motiva

A dor chegou como relato de uso, não como bug: o financeiro precisava **liquidar as
parcelas de uma venda**. O fluxo real era: filtrar a lista do Financeiro pela
venda → abrir o detalhe da parcela → conferir → dar baixa → "Voltar". E o "Voltar"
jogava na **raiz do módulo, com filtros e paginação zerados** — porque era um
`router.push` fixo para a raiz do módulo.

Refazer filtro + paginação a cada parcela. Agora imagina **dois anos de histórico,
parcela por parcela**: o custo de cada baixa não era a baixa — era reencontrar o lugar.

O diagnóstico ampliado mostrou que não era um botão: era o **padrão da casa**. Filtros
viviam em `useState` puro (perdidos em qualquer navegação), abas liam `?aba=` só na
montagem (trocar de aba não gravava na URL), e a lista do Financeiro nem aceitava
deep-link filtrado — o atalho de outro módulo caía na lista genérica. E havia sete
"idas sem volta" entre módulos (multa emitida sem link para a fatura gerada, ficha da
pessoa sem link para o próprio extrato, número do contrato exibido
como texto puro…).

## 2. Auditoria medida ANTES de opinar

Regra do método (§2): nenhuma fase começa com opinião. Comandos prontos, da raiz do app web:

```bash
cd <pasta-do-front>

# (a) "Voltar" com destino fixo — push cego para path literal (confira quais são raiz de módulo)
grep -rnE "router\.push\('/[a-z/-]+'\)" src/app --include="*.tsx"

# (b) Quantas telas têm botão "Voltar" (denominador do percentual)
grep -rln '"Voltar\|>Voltar\|Voltar para' src/app --include="*.tsx" | wc -l

# (c) O modelo correto já existente (router.back) — quase sempre é raro
grep -rn "router.back()" src/app --include="*.tsx"

# (d) returnTo: existe mecanismo, ou só homônimos de estado interno de modal?
grep -rn "returnTo" src/app src/lib src/hooks --include="*.ts*"

# (e) Telas de lista com filtro em useState que NUNCA leem a URL
grep -rln "useState" src/app --include="<arquivo-da-tela>" | xargs grep -Ln "useSearchParams"

# (f) Abas: quem lê ?aba= na montagem vs quem grava de volta na troca
grep -rn "searchParams.get('aba')" src/app --include="*.tsx"
grep -rn "router.replace" src/app --include="*.tsx" | grep "aba"
```

No app do ciclo 2026 (auditoria de 2026-07-16, 3 varreduras paralelas em `<pasta-do-front>/src`):

- **~93% dos "Voltar" hardcoded** para a raiz do módulo — o número virou a manchete do PLAN;
- **um único** `router.back()` no sistema inteiro;
- **zero** mecanismo de `?returnTo=` (o único "returnTo" do grep era estado interno de
  modal — homônimo, não navegação);
- **nenhuma** tela de lista sincronizava filtro de volta para a URL; a do Financeiro
  tinha todos os filtros e a página em `useState` puro;
- 7 gaps de "ida sem volta" entre módulos, tabelados no PLAN;
- bônus da auditoria: um componente de breadcrumb existia e **nunca era usado**.

Os números definem o ranking (pior primeiro): o fluxo venda×Financeiro era a Fase 1.

## 3. O padrão-alvo — as 4 peças

### Peça 1 — Botão Voltar com fallback (nunca push fixo)

Um componente de botão sobre um hook de retorno. Precedência:

```
1. ?returnTo=   (validado pelo sanitizador — peça 2)
2. router.back() SE existe passo anterior interno NESTA aba
3. fallback declarado (raiz do módulo) — único caso em que o destino é fixo
```

O "passo anterior interno" vem de uma trilha curta em `sessionStorage`, alimentada a cada
troca de rota — sem ela, `router.back()` num deep-link colado **sairia do sistema**. A
trilha é consumida antes do `back()`, para que voltas encadeadas não enxerguem histórico já
consumido. O hook também monta os links de saltos cross-module já carregando o
retorno (derivado de `usePathname`/`useSearchParams`, não de `window` — href idêntico no
server e no client, senão quebra hidratação).

Uso: o botão recebe o fallback declarado (`/<modulo>`) e o rótulo "Voltar para <Modulo>".

### Peça 2 — Sanitizador de `returnTo` anti-open-redirect

`returnTo` é input do usuário na URL: sem validação vira open redirect. A regra: **recusar
todo redirecionamento para fora do domínio.** Só passa path interno relativo das áreas
permitidas; valor vazio, URL absoluta, protocol-relative (`//host`, `/\host`), backslash e
control chars, esquema embutido (`/javascript:`) e path fora das áreas permitidas são
recusados, inclusive quando chegam encodados. Cada vetor tem caso no teste adversarial.
**Todo consumo de `?returnTo=` passa pelo sanitizador** — inclusive na hora de MONTAR o
link, não só na hora de seguir.

### Peça 3 — Filtros e abas na URL

- **Abas**: um hook de aba na URL —
  `router.replace(..., { scroll: false })` (trocar aba não é passo de histórico), aba
  padrão SAI da URL (link limpo), e a troca lê `window.location.search` no momento do
  clique para não pisar em params de outros donos da mesma URL (filtros, `?returnTo=`).
- **Filtros**: hidratação via initializer do `useState` a partir de `useSearchParams()`
  (sem loop), espelhamento de volta com `router.replace` sem scroll reset e debounce em
  campos de texto; `setPage(1)` em TODA troca de filtro; `push` jamais (não poluir o
  histórico com cada tecla).

### Peça 4 — Deep-links estáveis

Toda lista filtrável é linkável: os MESMOS params que a tela grava ela lê
(`?status=`, `?<entidade>Id=`, `?aba=`, `?busca=`). É isso que
fecha as "idas sem volta": multa → `/<modulo>?<entidade>Id=` filtrado; ficha da pessoa →
`/<modulo>/<rota>?<entidade>Id=`. Deep-link é
consequência das peças 1–3, não feature à parte — e sai de graça.

## 4. Fases (anatomia do METODO §3 aplicada)

- **F0 — auditoria medida** (§2 acima): greps quantitativos, ranking pela dor, PLAN com
  os números como manchete. 30 minutos de grep valem mais que qualquer opinião.
- **F1 — as 4 peças + piloto no fluxo mais dolorido, com gate do dono.** No app do ciclo 2026:
  Financeiro inteiro (filtros na URL + Voltar do detalhe + deep-link por venda + link de
  ida ancorado na venda). Gate = validação manual do dono no navegador: venda → link para
  as faturas da venda → baixa da 1ª parcela → detalhe da 2ª → voltar → **recorte
  intacto** → baixa da 2ª sem refazer nada.
- **F2 — migração tela a tela**, por lotes rankeados: os "Voltar" fixos migrados
  para o botão Voltar com fallback + propagação de `returnTo` nos saltos cross-module;
  gaps de ida-sem-volta (com 2 desvios registrados e depois endossados na
  auditoria); abas 100% na URL. Escopo por fase é lei: cortes declarados no
  handoff (filtros de listas sem rota de detalhe ficaram de fora — aceito pelo auditor).
- **Spec permanente** de navegação-retorno — 8 testes: filtro
  sobrevive a detalhe+voltar; deep-link hidrata; deep-link direto cai no fallback (aba
  NOVA, para isolar histórico); `?returnTo=` interno tem precedência; `returnTo` externo
  é IGNORADO (anti open-redirect provado com `evil.example.com`); `?<entidade>Id=` recorta as
  parcelas da venda de teste; o fluxo da dor completo, 2 parcelas em série; troca de aba grava `?aba=`.
  Padrão clique-que-navega **à prova de corrida** (lição E3, endurecida depois no ciclo
  de harmonia):

  ```ts
  await Promise.all([
      page.waitForURL(/\/<modulo>\/[^/?]+/),
      detalhes.click(),
  ]);
  ```

  `waitForURL` começa a escutar ANTES do clique e usa a janela cheia de 30s.

## 5. Armadilhas pagas (não repita)

1. **Open-redirect via `returnTo`.** Todo mecanismo de retorno por query param é um
   open redirect à espera de acontecer — por isso o sanitize é obrigatório desde o
   primeiro commit, cobre os vetores esquisitos (`//`, `/\`, control chars, esquema
   embutido, valor encodado) e tem teste E2E adversarial dedicado. Nunca "valido depois".
2. **Spec frágil de navegação sob seed denso.** `click()` + `expect(page).toHaveURL()`
   com timeout de 5s funciona com banco magro e quebra sob seed denso: o snapshot da
   falha JÁ mostrava a página de destino — a navegação só COMMITOU depois dos 5s. O
   idioma correto é `Promise.all([waitForURL, click])` (lição E3). Corolário do método:
   medir/testar com seed denso, senão o verde é piso, não teto.
3. **Spec que assere a implementação, não o comportamento.** Uma spec antiga asserava
   `a[href="/<modulo>"]`; quando o "Voltar para <Modulo>" virou o botão Voltar
   (button, não link), ficou vermelha sem regressão real. Assere o
   destino da navegação (`waitForURL`), não o elemento.
4. **Fixture E2E órfã = 500 permanente.** As vendas criadas pelo próprio spec (prefixo
   `E2E`) precisam de limpeza registrada no script de limpeza de E2E; venda cujo
   comprador foi apagado deixava `/<modulo>/<rota>` em 500 no banco local. E o
   cleanup ganhou uma checagem de banco local como primeira linha (recusa host não-local
   salvo liberação explícita por variável de ambiente) — ressalva única da auditoria.
5. **Homônimo no grep da auditoria.** "returnTo" já existia no código como estado
   interno de modal — sem ler o contexto de cada hit, a auditoria medida teria contado
   mecanismo onde não havia. Grep conta; olho classifica.
