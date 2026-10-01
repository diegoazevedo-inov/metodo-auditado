---
name: auditar-responsividade
description: Auditoria MEDIDA do eixo responsividade/harmonia — % de páginas sem classe responsiva, nowrap, larguras fixas, tabelas sem container — e devolve o esqueleto do PLAN H0→H2 com ranking. Não corrige nada. Use quando telas cortam/estouram em mobile/tablet ou não há padrão de layout entre telas.
---

Auditoria medida do eixo RESPONSIVIDADE/HARMONIA. NÃO corrija — meça, rankeie, proponha.
Método completo: `remediacao/30-eixo-responsividade.md` (o mais denso do kit — leia
antes de propor fases).

## 1. Medir (estático — a varredura programática é a fase H0, não esta skill)

```bash
SRC=<dir das páginas>
TOTAL=$(find $SRC -name 'page.tsx' | wc -l)
SEMRESP=$(grep -rL -E '\b(sm|md|lg|xl):' $(find $SRC -name 'page.tsx') | wc -l)
echo "páginas sem NENHUMA classe responsiva: $SEMRESP de $TOTAL"
grep -rn "whitespace-nowrap" $SRC --include='*.tsx' | wc -l
grep -rnoE 'w-\[[0-9]+(px|rem)\]|min-w-\[[0-9]+' $SRC --include='*.tsx' | wc -l
grep -rn "truncate" $SRC --include='*.tsx' | grep -v "title=" | wc -l
grep -rln "<table" $SRC --include='*.tsx' | wc -l   # × quantos têm overflow-x-auto?
grep -rn "min-w-0" $SRC --include='*.tsx' | wc -l   # baixo = grids sem proteção
```

Inspecione: existe page-shell/gabarito compartilhado? Guard de layout? Varredura como
spec? Seeds densos (medição em tela vazia é piso, não teto)?

## 2. Reportar

- Tabela de métricas + top ofensores + fundações (gabarito/guard/varredura: sim/não).
- Esqueleto do PLAN: **H0** instrumentação (detector de estouro por ELEMENTO + varredura +
  assinatura sha256 como prova + matriz de viewports decidida pelo dono)
  · **H1** gabarito (page-shell, tabela, truncation) + guard-catraca + piloto 2 telas com
  GATE VISUAL · **H2** migração por lotes rankeados pela baseline (aceite: defeitos=0 +
  catraca baixada + screenshots 2 temas + E2E do módulo).
- Perguntas ao dono: matriz de dispositivos real? superfícies mobile-FIRST (operação em
  campo)? densidade tipográfica entra?

## 3. Nunca

Números estimados; migração antes do gate; detector confiado sem prova sintética;
varredura em tela vazia como veredito.
