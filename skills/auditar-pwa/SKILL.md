---
name: auditar-pwa
description: Auditoria MEDIDA do eixo PWA — runtimeCaching real vs. política segura por tipo, manifest (orientation/theme_color/ícones), prova de que o SW INSTALA de verdade e fluxo de update — e devolve o plano H3. Não corrige nada. Use quando o app tem (ou vai ganhar) PWA, especialmente se lida com dado financeiro/autenticado.
---

Auditoria medida do eixo PWA. NÃO corrija — meça e proponha. Método completo:
`remediacao/40-eixo-pwa.md`. Pré-condição: o eixo responsividade saudável
(instalar como app uma tela que estoura é embalar defeito).

## 1. Inspecionar (com evidência arquivo:linha)

- `runtimeCaching`: é o DEFAULT da lib? Existe regra NetworkOnly para TODO dado vivo
  autenticado — `/api` E caminhos de arquivos autenticados (`/uploads`, comprovantes)?
  (Workbox IGNORA `Cache-Control: private` — a regra tem que ser explícita.) Ordem das
  regras (a 1ª que casa vence)? Fallback de navegação → página offline?
- Manifest: `orientation` travada? `theme_color` fixo num app com 2 temas? Ícones
  maskable/apple-touch/splash? `start_url` autenticável?
- **O SW INSTALA DE VERDADE?** Prova por estado FINAL em build de produção (porta
  isolada): `active.state === 'activated'` + `navigator.serviceWorker.controller`.
  Lighthouse NÃO prova SW (a categoria PWA do LH 11.x não tem auditoria de SW — já
  deu 100 sobre um SW que nunca instalou). Atenção app-router: `fallbacks.data`
  precacheia caminho de pages-router → 404 → install `redundant`.
- Update flow: `skipWaiting`? Aviso ao usuário (toast do design system, nunca
  `confirm()`)? `Cache-Control` do `/sw.js` em produção (precisa revalidar)?
- Higiene de ambiente: SW de teste desregistrado ao final? dev-reset? build nunca
  durante E2E?

## 2. Reportar

- Tabela: item × estado real × risco (o pior: dado autenticado em CacheFirst — retenção
  pós-logout).
- Plano H3: política por tipo (tabela pronta no eixo) → manifest theme-aware + ícones →
  update flow → spec de PWA com as provas de estado final (com login, alvo que falharia
  sem o fix, desregistro ao final) → Lighthouse como complemento, nunca como prova.
- Perguntas ao dono: offline só-leitura ou com fila de sync (escopo próprio)? orientation?

## 3. Nunca

Confiar em Lighthouse como prova de SW; cachear dado autenticado "porque é imagem";
testar SW no servidor de dev.
