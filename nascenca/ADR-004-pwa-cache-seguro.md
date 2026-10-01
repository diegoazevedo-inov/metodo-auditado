# ADR-004 — PWA: política de cache POR TIPO + prova de SW por estado final

**Status**: modelo (adotar no dia 0, antes do primeiro `fetch` passar por um service worker)
**Origem**: ciclo Harmonia/PWA do app do ciclo 2026 — os dois achados CRÍTICOS da
auditoria final (documento autenticado em CacheFirst; SW que nunca instalou com todas as
provas verdes) custaram uma mini-rodada inteira. No dia 0 custam zero.

## Decisão

1. **A política de cache do SW é declarada POR TIPO, explicitamente, ANTES do primeiro
   deploy com SW** — nunca o `runtimeCaching` default do plugin (que serve qualquer API com
   NetworkFirst genérico: em app com dado vivo, é servir saldo/fatura stale sem ninguém saber).
2. **Dado autenticado NUNCA entra em cache — e isso inclui uploads, não só API.**
3. **A prova de que o SW funciona é por ESTADO FINAL** (`activated` + `controller`), como
   spec E2E contra build de produção, desde o primeiro build que embarca SW.

## Tabela padrão (ponto de partida — a ordem IMPORTA: workbox casa a 1ª regra que bater)

| # | Padrão | Estratégia | Por quê |
|---|---|---|---|
| 1 | `/api/*` same-origin | **NetworkOnly** | dado vivo nunca stale; offline → falha → /offline |
| 2 | `/uploads/*` same-origin (todo path de documento autenticado) | **NetworkOnly** | espelha a regra 1 — ver "a regra que faltou" |
| 3 | estáticos com hash (`/_next/static`, fontes) | CacheFirst 1a | imutáveis |
| 4 | imagens otimizadas (`/_next/image`) | StaleWhileRevalidate | — |
| 5 | imagens (`png/jpg/svg/ico/webp`) | CacheFirst 30d | versionadas |
| 6 | navegação (`request.mode==='navigate'`) | NetworkFirst timeout 3s → `/offline` | shell fresco, nunca dado |
| 7 | cross-origin | NetworkOnly | terceiros não cacheiam |

**A regra que faltou no app do ciclo 2026 (achado A1, crítico):** sem a regra 2, um comprovante
`/uploads/*.jpg` casa o CacheFirst de imagem e **persiste no dispositivo pós-logout**,
servido sem reautenticação. `Cache-Control: private` NÃO protege — **o runtime caching do
Workbox ignora headers**: decide pelo urlPattern. Toda rota nova de documento autenticado
nasce com regra NetworkOnly e asserção espelho na spec.

**Offline é só-leitura por padrão.** Fila de sync de escrita offline é decisão do dono, em
ADR próprio, com fluxos NOMEADOS no allowlist — nada com implicação financeira entra.

## Prova obrigatória (spec desde o 1º build com SW)

- Roda contra **build de produção em porta isolada** (SW não existe em dev); `test.skip` fora dela.
- Exige `reg.active.state === 'activated'` **E** `navigator.serviceWorker.controller` —
  nunca aceitar `installing` (SW que falha o install passa por `installing` → `redundant`;
  foi assim que uma PWA "verde" ficou semanas sem instalar). **Lighthouse não prova SW** — a
  categoria PWA do LH 11.x não tem auditoria de service worker; o 100 sai com SW morto.
- Asserção negativa **não-vácua**: com LOGIN (≥1 request `/api` real assertida) e alvo de
  uploads com extensão que CASARIA a regra de imagem (`.jpg`); controle positivo (um estático
  que DEVE cachear) prova que o CacheFirst está vivo e a exceção pré-empta de fato.
- A spec desregistra o SW e limpa caches ao final (não envenenar o resto da suíte).

## Consequências

- Todo endpoint novo de dado vivo nasce sob `/api/*` (ou path coberto pela regra 1) — criar
  prefixo fora das regras NetworkOnly exige atualizar tabela + spec no MESMO commit.
- Update de SW: `skipWaiting:false` + toast do design system (nunca `confirm()`) + reload
  único pós-aceite; `Cache-Control` do `/sw.js` no proxy = revalidação (senão correções da
  própria política de cache não chegam).
- Custo no dia 0: ~100 linhas de config + 1 spec. Custo de adotar depois: 2 achados críticos
  de auditoria, uma mini-rodada e a descoberta de que a PWA nunca instalou.
