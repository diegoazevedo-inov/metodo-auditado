# Eixo 4 — PWA (remediação)

> **Pré-requisito: base sólida.** PWA é o eixo "premium" da anatomia do ciclo (METODO.md §3,
> FASE 3) — só entra DEPOIS da responsividade zerada e do tema estável. Instalar um app que
> estoura em 390px ou serve saldo stale é embalar defeito para o bolso do usuário. No app do ciclo 2026,
> a H3 só começou com o placar de estouro em ZERO (assinatura vazia) e os guards de tema/layout
> como catraca. E mesmo assim a fase rendeu a descoberta mais humilhante do ciclo: **a PWA
> "pronta" nunca tinha instalado de verdade** (§5 abaixo). Este eixo existe para que você não
> repita isso.

---

## 1. Auditoria medida: o que inspecionar (antes de opinar)

Números e fatos verificáveis, não impressões. Meia hora de inspeção responde:

| # | Pergunta | Como medir | Red flag |
|---|---|---|---|
| 1 | O `runtimeCaching` é o DEFAULT do plugin? | ler `next.config.ts` (ou equivalente); default do @ducanh2912/next-pwa serve QUALQUER API com NetworkFirst genérico | app financeiro/autenticado com default = risco REAL de saldo/fatura/extrato stale servido do cache |
| 2 | Rotas de DOCUMENTO autenticado (`/uploads`, `/files`…) têm regra própria? | grep dos paths de upload nos DTOs/proxy + conferir se alguma regra do SW os cobre | sem regra, um `.jpg`/`.png` autenticado cai no CacheFirst de imagem (ver §2 — a lição paga) |
| 3 | `manifest.json`: `orientation` travada? `theme_color` fixo num app de 2 temas? | ler o manifest | `orientation:"portrait"` mata tablet/desktop instalado; theme_color único deixa a barra do SO errada em um dos temas |
| 4 | Ícones: `purpose:"maskable"` separado do `"any"`? apple-touch? splash iOS? | ler manifest + `ls public/icons` | maskable ausente = ícone cortado no Android; iOS sem apple-touch/splash = experiência quebrada |
| 5 | O SW **instala e ATIVA de verdade**? | DevTools → Application → Service Workers num build de produção: `active.state === 'activated'` E `navigator.serviceWorker.controller` truthy pós-reload | "registered" NÃO basta — `installing → redundant` é falha silenciosa (§5); Lighthouse 100 não prova SW (LH 11.x não tem auditoria de SW na categoria PWA) |
| 6 | Existe fluxo de update? | procurar handler de `waiting`/`controllerchange` | sem fluxo, usuário fica preso na versão velha até o browser decidir; `skipWaiting:true` cego troca versão no meio da sessão |
| 7 | Existe fila offline de ESCRITA herdada? | grep por background-sync / queue / IndexedDB de replay | fila que enfileira fluxo com implicação financeira contradiz "dado vivo nunca duvidoso" — vira decisão do dono (no app do ciclo 2026, um fluxo com implicação de faturamento foi REMOVIDO do allowlist) |

O resultado vira a manchete do PLAN da fase (ex.: "runtimeCaching default + 0 regra para
/uploads + orientation travada + SW nunca ativou").

---

## 2. A política de cache POR TIPO (a tabela real do app do ciclo 2026)

Regra de ouro: **dado vivo NUNCA sai do cache.** E a ordem IMPORTA — o workbox casa a
PRIMEIRA regra que bater, então as exceções NetworkOnly vêm ANTES das regras genéricas de
asset. Tabela real:

| # | Padrão | Estratégia | cacheName | Por quê |
|---|---|---|---|---|
| 1 | `/api/*` same-origin | **NetworkOnly** | `<nome-do-cache>` | TODO dado vivo (saldo, fatura, extrato, de qualquer área) — nunca stale; offline → falha → /offline |
| 2 | `/uploads/*` same-origin | **NetworkOnly** | `<nome-do-cache>` | documento AUTENTICADO (comprovante, contrato) — ver a lição abaixo |
| 3 | `/_next/static/*` | CacheFirst 1a | `<nome-do-cache>` | imutável (hash no nome) |
| 4 | fontes (`woff2`…) | CacheFirst 1a | `<nome-do-cache>` | imutável |
| 5 | `/_next/image?url=…` | StaleWhileRevalidate 30d | `<nome-do-cache>` | imagem otimizada |
| 6 | imagens (`png/jpg/svg/ico/webp`) | CacheFirst 30d | `<nome-do-cache>` | versionadas |
| 7 | navegação (`request.mode==='navigate'`) | NetworkFirst timeout 3s | `<nome-do-cache>` | shell fresco; offline → /offline (fallbacks.document). NetworkFirst de navegação nunca serve DADO stale — só o shell já baixado |
| 8 | cross-origin | NetworkOnly | `<nome-do-cache>` | terceiros nunca cacheiam (custo zero se o app usa `next/font` local) |

**A lição paga (achado A1, CRÍTICO, da auditoria final):** a regra 2 NÃO existia na primeira
entrega. Um comprovante de pagamento em `/uploads/*.jpg` casava a regra 6 (CacheFirst de
imagem, 30 dias) e um PDF de contrato navegado casava a de navegação — o documento financeiro
**persistia no cache do dispositivo PÓS-LOGOUT** e era servido sem reautenticação. E não há
defesa do servidor: **`Cache-Control: private` é IGNORADO pelo runtime caching do Workbox**
(ele decide pelo urlPattern, não pelo header). Todo path de documento autenticado precisa de
regra NetworkOnly explícita, espelhando a do `/api` — e de asserção espelho na spec (§5).

**Offline é só-leitura por padrão.** O cache do SW nunca serve dado vivo (regras 1–2);
navegação offline cai na página `/offline` informativa. Fila de sync de escrita offline é
DECISÃO DO DONO com escopo próprio — no app do ciclo 2026 uma fila pré-existente (herança de outro
módulo) enfileirava fluxos de escrita, um deles com implicação de faturamento; a fase
DOCUMENTOU e perguntou, o dono decidiu RESTRINGIR (fluxo financeiro fora do allowlist).
Nunca herde uma fila em silêncio, nunca a desligue por conta própria.

---

## 3. Manifest theme-aware (app com 2 temas)

- **`orientation` DESTRAVADA** (chave ausente do manifest — decisão do dono registrada).
  Portrait travado quebra tablet/desktop instalado; a spec assere `orientation === undefined`.
- **`theme_color`/`background_color` do manifest = a cor do tema DEFAULT** (`<valor>`, o
  fundo escuro — casa o splash). O manifest não é theme-aware; quem acompanha o tema é a meta:
  - **1º paint (SSR)**: `viewport.themeColor` do Next emite **duas metas** `theme-color` com
    `media="(prefers-color-scheme: …)"` — o SO acerta antes de qualquer JS;
  - **pós-hidratação**: um componente cliente sincroniza com o tema RESOLVIDO do app
    (cobre `system`, modo agendado E o toggle in-app) atualizando **SÓ o atributo `content`**
    das metas existentes — as duas ficam com a mesma cor, então o toggle vence a media.
  - **A lição paga (achado A5, CRÍTICO): NUNCA remover/mutar a ESTRUTURA de meta gerenciada
    pelo React.** A primeira versão fazia `removeAttribute("media")` + `.remove()` nos nós do
    `viewport.themeColor` → `Uncaught TypeError: removeChild` + hydration error que EM DEV
    derrubava a navegação inteira (spec de uma área autenticada vermelha, browser preso no login).
    Mutar `content` de nó existente é seguro; criar nó PRÓPRIO (defensivo, quando nenhum
    existe) é seguro; tocar na estrutura que o React reconcilia, nunca. Aceite: spec do
    módulo afetado verde + asserção de **0 erros de hidratação no console**.
- Valores vêm dos tokens (`--background` de cada tema) — nunca invente um hex terceiro.

**Ícones** (script de geração versionado, sharp, a partir do SVG canônico do app):
maskable 192/512 com **logo a 64% (safe-zone** — dentro do círculo de 80% que o Android
garante), `icon` 192/512 `purpose:"any"` com fundo, apple-touch-icon 180 (logo 72%, iOS
arredonda os cantos), e 6 splash iOS portrait (SE/X/12/ProMax + iPad + iPad Pro) via
`<link rel="apple-touch-startup-image">`. Manifest com `"any"` e `"maskable"` em entradas
SEPARADAS (um ícone `"any maskable"` é pior nos dois usos). Script versionado = ícones
regeneráveis quando a identidade mudar.

---

## 4. Fluxo de update do SW

Deploy não pode nem prender o usuário na versão velha nem trocar versão no meio da sessão:

- **`skipWaiting: false`** — numa ATUALIZAÇÃO o SW novo fica `waiting` até o usuário aceitar.
- **`clientsClaim: true`** — na 1ª instalação o SW ativa e assume a página na hora (o offline
  e a checagem de controller dependem disso). Os dois não brigam: clientsClaim age na
  ativação, que no update só acontece após o skipWaiting manual.
- Componente observador: detecta o `waiting` (ou `updatefound` →
  `installed` **com controller já ativo** = é update, não 1ª instalação) e mostra **TOAST do
  design system** — "Atualização disponível" + ação "Atualizar", persistente, top-center,
  `max-w-sm` (provado por screenshot em 390 nos 2 temas). **NUNCA `window.confirm()`.**
- Ao aceitar: posta `{type:'SKIP_WAITING'}` ao SW waiting (um `importScripts` de 3 linhas
  chama `self.skipWaiting()`), e o `controllerchange` recarrega a
  página **UMA vez, e SÓ se o usuário aceitou** (flag `<flag>`): sem essa proteção, o
  `controllerchange` que o clientsClaim dispara na 1ª instalação recarregaria a página à toa
  no primeiro acesso.
- Quem REGISTRA é o plugin (`register: true`) — registro manual "para controlar melhor" não
  persistia em alguns loads; o componente só OBSERVA. Poll de `reg.update()` a cada 1h.

---

## 5. A PROVA — a parte mais importante (a descoberta)

A H3 entregou "SW registra ✅, Lighthouse PWA 100 ✅". A auditoria re-executou as duas provas
e ficaram verdes. **E o SW nunca tinha instalado.** Reproduzir a prova ≠ validar a premissa
da prova (METODO.md §5.6):

- **Causa**: `fallbacks.data: "/offline-data.json"` do next-pwa precacheia
  `/_next/data/<buildId>/offline-data.json` — convenção do **pages-router**, rota que **não
  existe no App Router** → 404 no precache → `bad-precaching-response` → o install rejeita
  INTEIRO → SW `installing → redundant`, para sempre. Fix: remover `fallbacks.data`
  (`document` e `image` ficam — servem 200).
- **Por que passou**: o helper de espera aceitava `reg.active || reg.installing ||
  reg.waiting` — e um SW que FALHA o install passa por `installing` antes de virar
  `redundant`. Falso-positivo estrutural. E **o Lighthouse deu 100 mesmo assim: a categoria
  PWA do LH 11.x NÃO tem auditoria de service worker** — o 100 mede instalabilidade de
  manifest, não SW funcionando. Lighthouse é complemento, jamais a prova.

A prova REAL, endurecida (a spec de PWA, o gabarito):

1. **Estado FINAL, nunca transitório**: `reg.active.state === 'activated'` **E**
   `navigator.serviceWorker.controller` truthy (o SW INTERCEPTA os fetches desta aba — sem
   controller, as regras de cache nem estão no caminho das requisições).
2. **Build de produção em porta isolada** (`<variavel-de-ambiente>=1`, `next start -p <porta>`); fora dela a
   spec dá `test.skip` — em dev não há SW e o vermelho mentiria.
3. **A prova negativa não pode ser vácua**: asserção "/api e /uploads nunca em cache"
   **exercitada COM LOGIN** (contador exige ≥1 request `/api` REAL — sem login a asserção
   passa por inanição) e com alvo `/uploads/*.jpg` — a extensão importa: um `.jpg` CASARIA o
   regex do CacheFirst de imagem se a NetworkOnly não pré-emptasse; um `.pdf` não casa regra
   nenhuma e a prova é vácua (achado M6).
4. **Controle positivo**: um ícone estático que casa a MESMA regra de imagem DEVE aparecer em
   cache (poll — o `cache.put` do Workbox é assíncrono — + `ignoreSearch` por causa do
   `?__WB_REVISION__`). Se isto cacheia e o /uploads não, a exceção está mesmo pré-emptando.
   Detector que nunca ficou verde-e-vermelho na sua frente não provou nada (METODO.md §4.3).
5. **Defesa em profundidade**: baixar `/sw.js` compilado e asserir que os `cacheName` (`<nome-do-cache>`) das
   duas regras NetworkOnly estão lá.
6. **A spec desregistra o SW + limpa caches ao final** (afterAll E em cada teste que
   registra) — senão ela envenena os E2E seguintes no mesmo host.

---

## 6. Disciplina de ambiente (a armadilha do SW)

O SW só existe em build de PRODUÇÃO (next-pwa desliga em dev) — e um SW registrado no host
errado envenena tudo que rodar depois. Rede de proteção em camadas, todas reais no app do ciclo 2026:

- **Porta isolada**: o build de prod roda em `:<porta>` — outra origem, o SW registra lá e não
  toca o dev `:3000`. Conferir que o proxy `/api` do app funciona também sob `next start`.
- **Reset de SW em dev**: em dev/localhost, um componente desregistra qualquer SW e limpa todos os
  caches no load — recuperação automática de acidente.
- **Componentes de PWA com guard de `NODE_ENV`** (update-prompt só age em produção).
- **NUNCA `build` com suíte E2E em andamento** (METODO.md §5.2 — o watcher recompila no meio
  e o vermelho mente).
- **A prova de não-envenenamento é um teste**: rodar o E2E núcleo em dev DEPOIS dos testes de
  produção — verde = o dev não ficou com SW/cache residual. (Foi exatamente essa alegação que
  o bug A5 invalidou na primeira entrega — a suíte pós-produção pegou.)
- **Deploy**: o `Cache-Control` do `/sw.js` no proxy reverso precisa revalidar
  (`max-age=0`/no-cache) — um sw.js cacheado agressivamente atrasa TODA atualização futura,
  incluindo correções de política de cache. Conferir no checklist de deploy, não depois.
  Pós-deploy: fumaça no domínio real — instala, `/uploads` de um comprovante segue exigindo
  auth e NÃO cacheia, toast de update aparece para quem tem o SW velho.

## 7. Aceite da fase

(a) varredura de responsividade re-executada — assinatura CONTINUA vazia (toast/metas/manifest
não estouram nada); (b) spec PWA verde no build de produção com as asserções endurecidas;
(c) Lighthouse como complemento (JSON versionado); (d) guards de tema/layout + tsc exit 0;
(e) E2E núcleo verde APÓS os testes de produção; (f) screenshots do toast e do /offline nos
2 temas. Handoff com ressalvas honestas (o que rodou sem login, o que é 404 local, hooks de
demo) — foi ressalva honesta que permitiu à auditoria achar o que importava.
