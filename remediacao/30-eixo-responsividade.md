# Eixo 3 — Responsividade/Harmonia (remediação)

O eixo mais denso do kit: nasceu do ciclo H0→H2 do app do ciclo 2026 (2026-07-20 → 2026-07-24), que levou
**60 rotas quebradas medidas → 0** em 4 lotes, com prova por assinatura sha256 e zero mudança de
comportamento auditada lote a lote. Tudo abaixo é regra paga com medição real. Os verificadores
deste eixo (detector de estouro, varredura, consolidador, catraca de layout) estão em `guards/`.

---

## 1. Auditoria medida (30 min de greps ANTES de opinar)

Nenhum número abaixo é opinião — cada grep vira manchete do PLAN e define o ranking de ataque.
Rode na raiz do frontend (ajuste `src/app` ao seu layout):

```bash
# % de páginas sem NENHUMA classe responsiva (sm:/md:/lg:/xl:)
total=$(find src/app -name "*.tsx" | wc -l)
sem=$(grep -rLE '\b(sm|md|lg|xl):' src/app --include="*.tsx" | wc -l)
echo "$sem de $total páginas sem classe responsiva"

# nowrap: com dado UPPERCASE longo, estouro garantido
grep -rn "whitespace-nowrap" src --include="*.tsx" | wc -l

# truncamento existente (pouco = texto dinâmico vaza)
grep -rnE "truncate|line-clamp|break-words" src --include="*.tsx" | wc -l

# truncate SEM title na vizinhança (esconde dado sem dar como ler)
grep -rn "truncate" src --include="*.tsx" | grep -v "title=" | head -30

# larguras fixas em px — cada uma quebra em alguma largura de tela
grep -rnE 'w-\[[0-9]+px\]' src --include="*.tsx" | wc -l

# tabelas × containers de rolagem (pareamento NÃO garantido pelo grep — ver §2)
grep -rln "<table" src --include="*.tsx" | wc -l
grep -rn "overflow-x-auto" src --include="*.tsx" | wc -l

# densidade: fontes ilegíveis persistentes
grep -rnE 'text-\[(9|10)px\]' src --include="*.tsx" | wc -l
```

No app do ciclo 2026: **34 de 85 páginas (40%) sem nenhuma classe responsiva**, 51 `whitespace-nowrap`,
só 56 truncamentos, 42 `w-[Npx]`, 28 arquivos com tabela × pareamento incerto, 1.351 fontes <11px.
Esses números viraram, na H0, **60 rotas quebradas medidas** — a estimativa por grep subestima e
superestima ao mesmo tempo; por isso a fase seguinte é instrumentar, não corrigir.

---

## 2. H0 — instrumentação (o coração do eixo)

Fase de MEDIÇÃO: proibido corrigir layout. Entregável = detector + varredura-como-spec + baseline
congelada por prova. Os três verificadores estão em `guards/`; aqui fica o papel de cada
um no processo. Como cada um mede está na documentação deles.

### 2.1 Os papéis

| Verificador | O que verifica | Quando entra | O que prova |
|---|---|---|---|
| Detector de estouro | estouro horizontal **por elemento** numa tela | chamado pela varredura e pela prova sintética (§2.5) | que o defeito existe e onde está |
| Varredura | o detector aplicado à matriz rota × viewport (§2.3) | baseline da H0, fechamento de cada lote da H2, aceite das fases seguintes | o placar do app inteiro, e que cada tela medida é a rota pedida (§2.4) |
| Consolidador | junta o resultado da varredura, separa defeito do shell de defeito de página e emite a assinatura sha256 dos defeitos de página | fim de cada varredura | que o placar é de UMA execução completa: recusa entrada incompleta ou de execuções misturadas |

A baseline congela quando **2 execuções independentes dão a mesma assinatura**.

### 2.2 O que o ciclo aprendeu medindo (resultado, não mecanismo)

- **Placar por página é cego.** No app do ciclo 2026 o shell não rola a página: a métrica de
  página devolveu zero defeito com o app podre. O placar tem de ser por elemento.
- **Falso-verde de instrumento: 0/48 rotas quebradas** (§5, armadilha 1).
- **Decoração não é defeito.** Glow de canto intencional contado como recorte inflava o placar:
  60 recortes → 19 reais + 43 decorativos (achado A2 da auditoria). O decorativo sai do placar e é
  listado à parte.
- **Isenção larga demais esconde defeito.** Intenção declarada (rolagem de tabela, truncamento
  explícito) não é defeito, mas uma isenção que valia além do devido só caiu por asserção
  sintética (achado C3b).
- **Defeito do shell conta uma vez.** Um defeito do shell compartilhado aparecia em ~128 rotas;
  sem separar shell de página, vira 128 "rotas quebradas".
- **Não-determinismo tratado na origem, nunca mascarado.** A baseline oscilava 44↔45 entre
  execuções e só congelou depois que cada fonte de instabilidade foi tratada (a última, B1), com 0
  medições instáveis na final.

### 2.3 Matriz de viewports — decisão do dono

390×844 / 768×1024 / 1440×900 em tudo + **piso de estresse 360×800** só nas superfícies
mobile-first (no app do ciclo 2026: as áreas que o dono apontou como de uso no celular, mais as públicas). As demais
telas não são cobradas em 360; o escopo é decisão do dono e fica registrado. Rotas públicas
(login/registro/offline) entram como área própria, medida DESLOGADA (a auditoria achou o login
vazando 76px fora da matriz original, achado A3).

### 2.4 Medir a rota errada — achado A1 (grave)

A sessão de uma área autenticada caía (401 → redirect ao login) e **8 medições eram, na verdade, da
tela de login** — parte das "quebras" dessa área era a home, e rotas reais dela tinham cobertura ZERO.
Requisito: tela medida diferente da rota pedida é FALHA da varredura, nunca registro. Bônus real:
investigar a causa do 401 achou **bug de produto** (endpoints `<rota>` com a anotação de acesso
errada — quebrados em prod desde o nascimento da feature).

### 2.5 Prova do detector — ele tem de ficar VERMELHO na sua frente

Spec com estouro sintético: o detector tem de reprovar o que foi plantado, inclusive a situação
que tinha dado o falso-verde 0/48, e aprovar depois que é removido. No app do ciclo 2026 terminou
com 9 asserções. Um detector que nunca reprovou nada não provou nada.

---

## 3. H1 — gabarito + piloto

Fase de GABARITO: componentes-lei + guard + 2 telas piloto (1 líder do ranking + a pior do app).
Gabarito documentado no `PADROES-layout.md` do projeto — cada regra fecha uma causa MEDIDA da H0.

### 3.1 Page-shell

Garante `min-w-0` **na raiz e no header** (filho de flex/grid tem `min-width:auto` e se recusa a
encolher — causa nº 1 de vazamento), título `truncate`+`title`, header que empilha no mobile
(`flex-col md:flex-row`), ritmo único. **Padding de página vem do LAYOUT** (área de conteúdo com `p-4
md:p-10`) — repetir `p-8` na página é padding DUPLICADO que espreme e estoura (causa direta medida
em 4 módulos na H2). Tela embedded/hub gigante que não couber
no componente recebe o fix de raiz equivalente (sem `p-8` + `min-w-0` + headers `flex-wrap`) — 
precedente aceito pela auditoria.

### 3.2 Tabela responsiva e o aviso do `[contain:paint]`

`<table>` SEMPRE dentro do container de rolagem — tabela densa de dado financeiro não cabe em 390px
sem virar ilegível; a escolha honesta é rolar, não amputar (o anti-padrão da H0: `overflow-hidden` em
volta de 5 tabelas, a pior com **450px de coluna inalcançável**). O container aplica `[contain:paint]`
porque, sem ele, **a tabela larga infla o `scrollWidth` dos ANCESTRAIS mesmo já rolando** (medido:
container `cw=356/sw=891` rolando e o `max-w-7xl` ainda reportando `sw=715`; nem `max-width:100%`
nem `overflow:hidden` resolviam). **Efeito colateral que VAI morder**: `contain:paint` recorta
qualquer `absolute`/`fixed` interno — o 1º dropdown/menu/tooltip aberto numa linha será cortado em
silêncio. Regra: **overlay em linha de tabela = portal, nunca `absolute` filho da célula**.
Armadilha de componente: a 1ª versão injetava `text-sm` na tabela e mudou o visual de uma tabela de
11px — regressão C1; tamanho de fonte é do chamador, não do container.

### 3.3 Célula de texto longo e as regras de texto

`truncate` + `title` com o valor COMPLETO. **Touch não tem hover** — o `title` é inalcançável no
dedo: pendência de a11y CONSCIENTE, registrada com plano (tap-para-expandir ou aria + affordance),
não implementada na fase de gabarito para não embutir comportamento. Regras:

1. **Número NUNCA trunca** (moeda/quantidade/saldo) — `R$ 123.4…` é mentira silenciosa. Use
   `break-words` ou grid que dê largura (`grid-cols-1` no estreito) + `min-w-0`. Caso medido: um KPI de
   valor da tela inicial vazava nos DOIS extremos (card estreito em 1440 E full-width em sm-lg).
2. `whitespace-nowrap` proibido em célula cujo conteúdo varia (legítimo em `<th>`, número, data).
3. `w-[Npx]` proibida sem escape hatch justificado (trilho decorativo de 2px, ok).
4. `min-w-0` em todo filho de flex/grid com texto que possa crescer.

### 3.4 Catraca de layout — BIDIRECIONAL

Cobra as quatro regras do gabarito das §3.2–3.3. Guard "zero ou falha" sobre 86 dívidas
legítimas seria desligado no 1º dia — então é CATRACA: a dívida **não pode subir** E, quando uma
dívida sai, o guard **falha até a baseline ser re-fixada** — senão a folga fica e a dívida re-sobe
sem alarme (buraco C2, provado em sandbox: reduzir→exit 0→re-aumentar→exit 0). Quando a migração
zerar, o modo estrito (zero) vira o gate definitivo. Prove a catraca plantando uma violação por
regra (exit 1 nomeando as 4) + escape hatch + os dois sentidos.

### 3.5 Piloto com gate do dono

2 telas: a líder do ranking (`<modulo>`) e a pior do app (outro `<modulo>`, 450px cortados) →
0·0·0 nos 3 viewports, screenshots antes/depois nos 2 temas (o "antes" por `git checkout <sha> --
src`, não de memória). Honestidade obrigatória: no app do ciclo 2026 o ganho da líder era "medido, não
visual" em mobile (hub embedded + clip do shell) — declarado, e o gate visual do dono olhou a tela
onde o ganho aparecia. Componente compartilhado tocado (barra de filtros, usada em várias telas) = prova por varredura
completa: **0 defeitos novos**, não opinião.

---

## 4. H2 — migração por lotes rankeados

Ordem = ranking da baseline (pior primeiro), 3–5 módulos por lote, auditoria adversarial entre
lotes. Trajetória real: 30 → 18 → 11 → 5 → **0** em 4 lotes, com a assinatura VAZIA no fim.

**Aceite por módulo (todos, sempre):**
1. **Defeitos de página = 0** nos viewports do módulo (+360 se mobile-first) — provado por
   `grep <modulo>` = 0 na assinatura nova.
2. **Guard baixado**: cada módulo fecha com a baseline da catraca re-fixada e commitada junto (86→79→72→70→67).
3. **Screenshots 2 temas × viewports** do módulo.
4. **E2E do módulo verde COM os seeds densos ativos** (nenhuma regressão de comportamento).

**Diff de assinatura justificado LINHA A LINHA, com 0 novas.** Cada linha que saiu pertence a uma
rota do lote — a exceção vira parágrafo próprio (Lote 1: 1 linha de rota não-tocada saiu porque o
`min-w-0` no date-picker compartilhado consertou de brinde; efeito colateral benéfico, PROVADO por
varredura). Linha nova em qualquer rota = regressão, lote não fecha.

**Seeds densos OBRIGATÓRIOS — módulo vazio é PISO, não teto.** A área do cliente medida com usuário-seed
esparso saiu 0 achados em `<modulo>` por estar VAZIO; outro `<modulo>` idem (0 registros no banco, achado K3
da auditoria). Seed denso (guard de banco local + idempotência por chave determinística +
kill-switch + fixture PERSISTENTE fora do cleanup E2E) **data-revelou** defeitos que o piso
escondia — glow de `<modulo>`, chips de filtro em 360, KPIs de valor estourando o
box — todos zerados ANTES de fechar o módulo. Nunca dê um módulo por resolvido medido no vazio.

**Densidade tipográfica junto** (mesma passada, não rodada extra): todo texto persistente ≥11px
(357+36+53+81+… conversões por lote); a auditoria confere que a densidade só SUBIU nos arquivos do
diff. Compressão ilegível não é overflow — o detector não a vê; a regra de densidade é quem trata.

---

## 5. Armadilhas pagas (todas reais — não repita)

1. **Instrumento falso-verde (0/48).** O detector chegou a devolver 0 de 48 rotas quebradas. Só
   não virou baseline porque 0 contradizia o grep da auditoria medida — quando o instrumento
   contradiz a auditoria, desconfie do instrumento.
2. **Métrica de página cega** — com o shell sem rolagem de página, ela deu 0 com 60 rotas podres.
   Placar por elemento, sempre.
3. **Decoração inflava o placar** — 60 "recortes" eram 19 reais + 43 glows intencionais; contados
   juntos, distorciam o ranking de ataque.
4. **Contaminação por sessão caída** — 401 → redirect, e 8 medições eram da tela de login.
   Conferir a rota medida; e o 401 em si era bug de produto que a medição achou.
5. **desktop-1440 degrada sob carga** de sessão longa de varredura (estourou o tempo limite em 3
   dos 4 lotes + na auditoria) — não é defeito de código: re-executar aquele viewport isolado. E
   **UMA varredura por vez**: a própria auditoria derrubou 2 viewports rodando provas paralelas no
   mesmo servidor.
6. **Medição com dado vivo não é byte-estável entre dias** (juros mudaram um campo de texto do
   relatório de um dia para o outro) — a prova canônica é a ASSINATURA sem texto/pixel, não o JSON.
7. **Fase de medição não corrige; fase de layout não muda comportamento.** Handlers movidos
   verbatim, diff só de className é auditável — foi o que permitiu 4 auditorias dizerem "zero
   mudança de comportamento" sobre ~26 commits.
