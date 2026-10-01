---
name: auditar-fluxos
description: Auditoria MEDIDA do eixo fluxos de UI-UX/navegação — conta "voltar" hardcoded, filtros fora da URL e abas sem deep-link, e devolve o esqueleto do PLAN F0→F2. Não corrige nada. Use quando usuários reclamam de perder contexto ao navegar (voltar cai na raiz, filtro some).
---

Auditoria medida do eixo FLUXOS/NAVEGAÇÃO. NÃO corrija — meça, rankeie, proponha.
Método completo: `remediacao/20-eixo-fluxos.md`.

## 1. Medir

```bash
SRC=<dir dos componentes>
VOLTAR=<nome do componente de retorno do projeto>   # substitua antes de rodar, como o SRC
# "voltar" hardcoded (push fixo p/ raiz de módulo) vs. componente com fallback
grep -rn "router.push(['\"]/" $SRC --include='*.tsx' | grep -iE "voltar|back|onClick" | wc -l
grep -rln "$VOLTAR" $SRC | wc -l   # 0 = a peça nem existe
# filtros em useState (não sobrevivem a navegação) vs. na URL
grep -rn "useState" $SRC --include='*.tsx' | grep -iE "filtro|filter|status|busca|search|aba|tab" | wc -l
grep -rln "useSearchParams\|searchParams" $SRC --include='*.tsx' | wc -l
# returnTo sem sanitização (risco de open-redirect)
grep -rn "returnTo" $SRC | grep -v "sanitize" | wc -l
```

Complete com o teste de mesa no fluxo mais repetitivo do produto (ex.: dar baixa em N
itens da mesma entidade): quantos cliques/perdas de contexto por item?

## 2. Reportar

- Números + o fluxo-história que dói (descreva o caminho real do usuário).
- Esqueleto do PLAN: **F0** medição · **F1** as 4 peças (voltar-com-fallback,
  sanitizador de returnTo, filtros/abas na URL, deep-links) + piloto no fluxo mais dolorido com
  gate do dono · **F2** migração tela a tela + spec permanente de navegação (padrão
  clique-que-navega: `Promise.all([waitForURL, click])`).
- Pergunta ao dono: qual fluxo é o mais repetitivo na operação real?

## 3. Nunca

returnTo sem sanitize (open-redirect); push fixo "só neste caso"; corrigir de passagem.
