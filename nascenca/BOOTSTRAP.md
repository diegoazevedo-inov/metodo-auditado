# Nascença — bootstrap de projeto novo (ANTES da primeira tela)

Meta: os 4 eixos custaram meses de remediação no app do ciclo 2026. No dia 0 custam horas, porque
a dívida simplesmente não nasce: **guard com baseline ZERO recusa a primeira violação**.

## Checklist do dia 0 (ordem importa)

### 1. Decisões do dono — registradas como ADR antes de qualquer código
- [ ] [ADR-001](ADR-001-tema-tokens-semanticos.md) — tema: 1 ou 2 temas? default? paleta?
- [ ] [ADR-002](ADR-002-navegacao-com-contexto.md) — navegação com contexto
- [ ] [ADR-003](ADR-003-layout-responsivo-gabarito.md) — gabarito + matriz de dispositivos
      (pergunte: qual o pior device REAL de usuário? mobile-first onde?)
- [ ] [ADR-004](ADR-004-pwa-cache-seguro.md) — vai ser PWA? política de cache POR TIPO
      decidida antes do primeiro fetch
- [ ] [ADR-005](ADR-005-medicao-e-guards.md) — medição-como-spec e guards no CI

### 2. Fundações no esqueleto do app
- [ ] Tokens semânticos no CSS global (tabela mínima no ADR-001) — e NENHUMA cor fora deles.
- [ ] Gabarito de layout: page-shell + componente de tabela + célula de texto longo
      (anatomia mínima no ADR-003). Toda tela nasce DENTRO do gabarito.
- [ ] Peças de navegação: voltar-com-fallback + sanitize de returnTo + filtro/aba na URL.

### 3. Guards e specs — baseline ZERO, no CI desde o primeiro commit
- [ ] Verificadores de `guards/` configurados para o projeto:
      paleta · contraste · catraca de layout · detector de estouro +
      varredura-como-spec + consolidador.
- [ ] Script agregador (`nome-do-projeto:check`) rodando TUDO — e no CI como gate.
- [ ] Baseline dos guards = **zero**. A catraca nunca sobe. (No app do ciclo 2026 ela nasceu em 86
      e custou 4 lotes descer a 67 — esse custo é o que você está evitando.)
- [ ] Seed denso idempotente desde o primeiro CRUD (guard de banco local + kill-switch)
      — medição honesta nunca em tela vazia.

### 4. Documentos vivos
- [ ] `CLAUDE.md` do projeto pelas seções-modelo de [templates/](templates/) (tema,
      harmonia, navegação, comandos de check).
- [ ] `PADROES-layout.md` iniciado.
- [ ] Fixtures de teste de DOCUMENTO/dados fiscais SEMPRE por gerador validado contra o
      DV real (lição CNPJ: validar na borda quebra todo teste com valor sintético).

### 5. Prova do bootstrap (o "hello world" do método)
- [ ] Plante 1 violação de cada guard e veja o CI ficar VERMELHO. Remova.
- [ ] Rode a varredura nas telas-esqueleto: assinatura vazia É a baseline congelada.
- [ ] A partir daqui: qualquer PR que estoure, hardcode cor ou quebre contraste **não
      entra** — e o custo disso foi zero.

## O que NÃO fazer no dia 0

- Não escrever tela "rapidinho pra ver no ar" fora do gabarito — a primeira exceção é
  a fundação da dívida.
- Não adiar o guard "até o design estabilizar" — o guard é exatamente o que deixa o
  design mudar barato depois.
- Não instalar os verificadores sem ler a documentação deles (âncoras de shell, tokens e
  rotas são do SEU projeto).
