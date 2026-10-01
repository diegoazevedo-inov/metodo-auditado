# Registro de decisões

A spec ([SPEC.md](SPEC.md)) fixa comportamento observável e critério de prova.
Tudo abaixo é decisão desta implementação. Os pontos que a spec marca como
**OPCIONAL** estão na primeira seção, cada um com a justificativa que ela
exige.

---

## 1. Pontos que a spec marca como OPCIONAL

### 1.1 GUARD 2 — como reconhecer que a tabela está contida
**Decisão: procurar a contenção entre os ancestrais, achados pela
indentação, *e* aceitar o componente-padrão pelo nome.** A alternativa era
aceitar só o componente-padrão.

**Por quê.** A catraca conta por arquivo e por regra, sem olhar a linha.
Isso tem uma consequência que pesa mais aqui do que num guard de
tolerância zero: um falso positivo em `arquivo X / regra 1` congela na
baseline e passa a **mascarar uma violação nova e verdadeira** da mesma regra
no mesmo arquivo — a contagem não sobe, e a catraca não reclama. Reduzir falso
positivo, portanto, não é conforto: é o que impede a catraca de ficar cega.
Um `<div className="overflow-x-auto">` escrito à mão em volta de uma tabela é
contenção legítima, e recusá-la só porque não é o componente-padrão criaria
exatamente esse ponto cego.

**Custo aceito.** A inferência depende de indentação consistente. Em código
mal formatado ela falha e devolve falso positivo, e também quando a tag do
ancestral traz a classe de rolagem numa linha seguinte à da abertura — está
declarado no cabeçalho do guard.

### 1.2 GUARD 3 — bordas e cores de destaque só de ornamento como informativos
**Decisão: NÃO classificar `--border` como ornamental.** Registrada junto da
tabela, em `pares-contraste.toml`, como a spec pede.

**Por quê.** Neste projeto a borda separa célula de tabela e delimita campo de
formulário: é ela que carrega a fronteira do controle. Fronteira de controle é
elemento de interface e responde pelo mínimo de 3:1 da norma. Rebaixá-la a
informativa seria comprar aprovação barata.

**Consequência real, e ela apareceu.** Na primeira execução o guard reprovou o
`--border` do próprio fixture: 1,49:1 no tema claro e 1,73:1 no escuro. Os
tokens foram corrigidos (`214 32% 84%` → `60%`; `217 33% 26%` → `42%`) até
fecharem em 3,09:1 e 3,10:1. Se a decisão tivesse sido "ornamental", os dois
valores continuariam lá, aprovados por definição.

Se um dia existir borda decorativa de verdade — divisória estética sem função
de delimitar controle — ela entra na tabela com `informativo = true` e com o
motivo escrito na mesma linha.

### 1.3 GUARD 4 — valor numérico do piso de severidade
**Decisão: 2,0 px.** A spec exige que o piso exista e seja justificado **por
medição**; o número é do projeto.

**A medição foi feita** (`proofs/experimento_piso.py`): duas execuções
completas, 5 viewports × 7 rotas, com piso **zero**. Resultado real:

```
achados com piso ZERO: execucao A = 44, execucao B = 44
instaveis (entram e saem entre execucoes): 0
maiores oscilacoes de magnitude entre as duas execucoes: delta 0.00px
distribuicao dos excedentes (execucao A):
    excedente <     2px :   0 de 44
    excedente <    10px :   0 de 44
```

**Leitura honesta do resultado: neste fixture o piso é inerte.** Não há nada
entre 0 e 10 px, e nada oscila. Ou seja, a medição **não** calibrou o valor —
ela provou que qualquer piso entre 0 e 10 px produz exatamente o mesmo placar
aqui, e portanto que 2,0 px é seguro (não pode esconder nada que tenha sido
medido). O fixture usa fonte de sistema, não carrega imagem e não busca dado.

**O que isso significa para quem adotar.** O procedimento está implementado e
é o entregável real deste item; o número 2,0 é um ponto de partida seguro, não
um valor calibrado. Um projeto com fonte web e imagem **precisa** rodar
`experimento_piso.py` contra as próprias rotas e fixar o seu.

### 1.4 GUARD 5 — uma largura extra, mais estreita, para as telas de celular
**Decisão: ADOTAR.** Viewport de 320×720 marcado com `piso_de_estresse = true`
em `rotas.toml`, e o parcial carrega a marca.

**Por quê.** 320 px não corresponde a nenhum aparelho corrente, e é de
propósito: é onde texto longo e tabela larga quebram primeiro. Além disso ele
aproxima uma condição comum e invisível na matriz de aparelhos — fonte
ampliada pelo sistema, que reduz a largura útil para perto de 320 px. Medir só
a partir de 390 px deixaria passar defeito que atinge quem mais precisa.

**Confirmado pela medição.** O placar do fixture em 320 px é **35**, contra
**21** em 390 px e **5** em 1280 px. O viewport de estresse encontra 14
defeitos que o de 390 px não vê.

**Alcance.** A largura de 320 px é medida em **todas** as rotas da matriz, as
públicas e as de operação inclusive, e não só nas telas pensadas para uso no
celular. A spec deixa ao projeto decidir em que telas medir; aqui são todas,
porque o fixture não separa telas de celular das demais, e medir a mais custa
tempo de execução, não achado falso.

---

## 2. Pontos em que a spec é ambígua ou omissa

### 2.1 GUARD 4 — quem entra no placar
A spec diz, nas regras de decisão do GUARD 4:

> **O placar é formado por três espécies: a do conteúdo que passa
> visivelmente da caixa, a do conteúdo escondido sem rolagem e a da rolagem
> horizontal não declarada.** A espécie decorativa é **excluída** dessa
> contagem e listada separadamente, de modo que elementos sem dano visível
> não aumentem o placar.

A implementação aplica essa regra como está escrita. Em
`uiguards/overflow_probe.js`, `NO_PLACAR` é o conjunto das quatro espécies
menos `recorte-decorativo`, e o comentário ao lado cita a frase acima. O teste
06 de `sweep/prova_sonda.py` exige `no_placar=False` para o recorte decorativo.

**Histórico.** Uma redação anterior da spec indicava as espécies do placar
pela posição: enumerava as quatro com a decorativa em terceiro lugar, mandava
"as três primeiras" para o placar e, na frase seguinte, mandava a decorativa
para fora dele. As duas frases não valiam juntas. A implementação adotou a
leitura que deixa a decorativa **fora** do placar: prevaleceu a frase que
trazia justificativa, porque um recorte que só atinge decoração não causa dano
visível, e uma rolagem horizontal que ninguém pediu causa. A spec foi depois
corrigida para nomear as três espécies do placar; a regra nova coincide com a
leitura adotada, e nenhum comportamento mudou.

### 2.2 GUARD 6 — a marcação da moldura, e o que fazer com `<html>` e `<body>`
A spec exige que a separação moldura/página dependa de uma marcação semântica
no layout raiz, sem ligação com o estilo, e deixa o mecanismo para quem
implementa, com a obrigação de documentá-lo. Ela não diz nada sobre o que fica
**fora** de toda marcação — a casca do documento.

**Mecanismo: dois marcadores**, `data-ui-frame` na moldura e
`data-ui-content` na área de conteúdo, configurados em `[medicao.ancoras]`
do `guards.toml`. A sonda registra, por achado, se ele está sob cada um.

**Regra: é defeito de PÁGINA o que está sob o marcador de conteúdo; todo o
resto é estrutura compartilhada**, inclusive a casca do documento. O
marcador de moldura não decide a classificação; ele existe para o guard de
âncora conferir que a marcação continua casando defeitos.

**Por quê, com número.** Com a regra inversa — moldura é o que está sob o
marcador de moldura, e todo o resto é página —, a primeira execução
classificou `html`, `html > body` e `body > div > main` como defeitos de
página, e o relatório saiu com **37 defeitos de página / 2 itens de moldura**.
`<html>` e `<body>` transbordam em **toda rota que tenha qualquer estouro** —
são exatamente a inflação que a separação existe para evitar. Com a regra
adotada, o mesmo estado dá **19 defeitos de página / 4 itens de moldura**, e o
ranking passa a apontar trabalho de verdade.

### 2.3 GUARD 5 — código de saída de falha da varredura
A spec não diz se destino divergente é `1` ou `2`.

**Resolução:** falha da varredura (destino divergente, cobertura de detalhe
encolhida, estado inicial não aplicado) → **1**; prova do detector reprovada,
navegador ausente ou configuração inválida → **2**.

**Por quê.** Destino divergente é um achado verdadeiro sobre a aplicação ou
sobre a sessão — a suíte executou e concluiu algo. Já um detector reprovado
significa que **o instrumento** está quebrado: não existe medição válida a
produzir, e nenhum parcial é gravado. Isso é literalmente "não consigo
executar", e confundi-lo com `1` seria o pior modo de falha que a spec nomeia.

---

## 3. Decisões livres (a spec deliberadamente não determina)

| Ponto | Decisão | Motivo |
|---|---|---|
| Linguagem | Python 3.13 nos seis | Uma linguagem só; `tomllib` e `hashlib` são stdlib. |
| Automação de navegador | Playwright (sync) com Chromium | Emula `reduced_motion` e `color_scheme` por contexto, que os GUARDS 4-5 exigem. |
| Framework de teste | `unittest` da stdlib | Deixa **Playwright como única dependência de terceiro** em toda a entrega. |
| Configuração | TOML | Aceita comentário — e quase toda entrada aqui exige motivo escrito ao lado. Leitor na stdlib. |
| Escape hatch | `ui-guard-allow[(guard)]: <motivo>` em comentário, motivo ≥ 10 caracteres não-brancos | Formato único nos guards estáticos; escopo opcional por guard. O mínimo recusa `: ok` e `: x`, que são exceção sem motivo. |
| GUARD 1, correlação de variantes (espécie 6) | O prefixo de variante do texto precisa **conter** o do fundo | `bg-primary` + `hover:text-white` correlaciona (∅ ⊆ {hover}); `hover:bg-primary` + `text-foreground` não. Evita falso positivo entre estados independentes. |
| GUARD 1, allowlist | Chaves relativas à raiz de UI | Caminho mais curto e estável que o relativo à raiz do projeto. |
| GUARD 6, "módulo" | Primeiro segmento do caminho da rota | Derivável da própria rota, determinístico, e agrupa lista e fichas do mesmo assunto no mesmo item de trabalho. |
| GUARD 6, seção extra | "Pontos acionáveis" (defeitos sem achado mais interno) | A spec exige que, quando vários elementos aninhados acusam o mesmo excesso, o relatório permita saber qual deles corrigir. Cada achado da sonda diz se tem outro achado dentro de si, e a seção usa esse dado para mostrar onde mexer. É derivada — **não** substitui a assinatura, que segue cobrindo todos os defeitos de página. |
| Saída em português | Mensagens, nomes e relatório | A spec é em português, e a mensagem de erro é lida por quem vai corrigir o código. |

---

## 4. Duas isenções que o próprio fixture exercita

Não são decisões de arquitetura, mas ficam registradas porque aparecem nas
provas:

- `fixtures/ui-src/components/BrandLogoMark.tsx` está na allowlist do GUARD 1
  porque os hexadecimais do logotipo são fixados pelo manual da marca e não
  podem virar token de tema. O motivo está escrito na própria entrada, e o
  guard **recusa executar** (código 2) se qualquer entrada da allowlist
  estiver sem motivo — provado.
- `/sair` e `/clientes/c-9999` estão fora da varredura, cada uma com motivo
  escrito em `rotas.toml`, e os motivos são copiados para dentro de cada
  parcial e para o relatório final — quem lê o relatório vê que a ausência
  foi escolha, e por quê.

---

## 5. Escolhas de comportamento em pontos que a spec deixa em aberto

### Comum e configuração

| Ponto | Decisão | Motivo |
|---|---|---|
| Escape hatch, posição | Marcador ao lado de código vale para a própria linha; sozinho na linha, vale para a seguinte | Cabe em "na própria linha ou na imediatamente anterior", e um marcador nunca isenta duas violações. |
| Configuração, tipo | Toda chave lida pelos guards tem tipo conferido; tipo errado é `2`. `familias`, `prefixos_cor` e `extensoes` também não podem vir vazias | Um valor reinterpretado em silêncio (texto como lista, texto como booleano) viraria aprovação. Lista vazia nessas três desligaria espécies inteiras. |

### GUARDS 1 a 3 (estáticos)

| Ponto | Decisão | Motivo |
|---|---|---|
| GUARDS 1 e 2, linha de importação | É importação só a linha cuja declaração termina no especificador de módulo entre aspas (`import`, `export … from`, `require`), no máximo com `;` e comentários. Cada comentário de bloco termina no primeiro `*/`; código entre dois comentários faz a linha ser avaliada | Uma reexportação de verdade termina assim. Qualquer outra forma com a palavra `from` é código de interface e tem de ser avaliada. |
| GUARD 1, notações modernas | Uma espécie só, `cor-funcional-moderna`, para `oklch()`, `oklab()`, `lab()`, `lch()`, `hwb()` e `color()`; `rgb-literal` e `hsl-literal` seguem separadas | A correção é a mesma para as seis (mover o valor para um token), então a dica de correção é uma só. |
| GUARD 1, `color()` | O literal de `color()` é um nome de espaço de cor seguido de número | O primeiro argumento de `color()` é o espaço (`display-p3`, `srgb`), não um número; exigir número, como nas outras, deixaria `color()` sempre de fora. |
| GUARD 1, `text-[..]` que é medida | Número com ou sem unidade, `calc`/`clamp`/`min`/`max` e a dica `length:` são medida; todo o resto é cor | O lado conservador: na dúvida o valor é tratado como cor e pode ser acusado, nunca o contrário. |
| GUARD 2, regra 4, onde procurar o atributo | Na tag do truncamento inteira, como na regra 3 | O atributo que torna o valor completo disponível é o da própria tag truncada. |
| GUARD 2, `line-clamp-N` | Conta como truncamento na regra 4 (`line-clamp-N` e `line-clamp-[..]`; `line-clamp-none` não) | A regra 4 da spec é "texto cortado cujo valor completo não esteja disponível por atributo acessível". O corte em N linhas esconde o valor do mesmo jeito que o corte em uma linha. |
| GUARD 2, classe de truncamento fora de tag | Acusada | Sem tag, não há onde procurar o atributo. Acusar é o lado conservador, e o escape hatch cobre o caso legítimo. |
| GUARD 2, baseline | A chave tem a forma `arquivo::regra`, com regra conhecida, e o último `::` separa a regra; a contagem é inteiro maior ou igual a zero — booleano não é contagem. Fora disso, `2` | Nenhuma regra contém `::`; um nome de arquivo pode conter. Baseline inválida é entrada inválida. |
| GUARD 2, `--modo refixar` | Grava qualquer contagem e sai `0`, nomeando as chaves que cresceram | A re-fixação é comando explícito de quem reduziu a dívida; recusar mudaria o contrato do modo, e a mensagem põe o aumento à vista de quem revisa. |
| GUARD 3, alfa | Alfa exatamente 1 (ou 100%) é opaco e segue calculado; **qualquer outro valor** é `2`, inclusive acima de 1 | Abaixo de 1 a cor efetiva depende do fundo, que o guard não conhece. Acima de 1 o CSS limitaria a 1, mas o valor é incomum o bastante para ser engano de digitação; recusar custa uma correção, e aprovar poderia esconder um par que ninguém conferiu. |
| GUARD 3, faixa dos canais | `rgb()` acima de 255 e saturação ou luminosidade acima de 100% são `2`; matiz fora de 0–360 é aceito e reduzido ao círculo | O navegador limitaria o canal, mas a cor que ele mostra não é a escrita; e o valor é incomum o bastante para ser engano. Matiz é ângulo e dá a volta por definição. |

### GUARD 4 (sonda de estouro)

| Ponto | Decisão | Motivo |
|---|---|---|
| Critério decorativo | O filho escondido é conteúdo se for interativo, se tiver texto visível, ou se for imagem ou gráfico (`img`, `picture`, `svg`, `canvas`) sem `aria-hidden`. Vídeo, `iframe`, `object` e `embed` são sempre conteúdo | A spec pede que o recorte decorativo não esconda "conteúdo perceptível ou interativo". O critério é **conteúdo**, não visibilidade: uma imagem ornamental se vê sem ser conteúdo, e `aria-hidden` é a forma padrão de o autor dizer isso. Texto visível é perceptível, e nenhum outro sinal o desfaz. Mídia e documento embutidos não são ornamento. |
| Texto gerado pelo estilo | Texto posto por `::before` ou `::after` conta como texto visível. O `content` é lido da esquerda para a direita, como o navegador o serializa: trecho entre aspas é texto (com `attr()` já resolvido e escapes decodificados numa passada só); fora das aspas, `url()`, `image-set()`, `image()`, `cross-fade()` e `element()`, com ou sem prefixo de fornecedor, são imagem; outra função (`counter()`, `counters()`, gradiente) e palavra-chave (`open-quote`, `close-quote`) não são lidas; o que vem depois de uma barra fora das aspas é texto alternativo e não conta. Não contam espaço, quebra de linha, largura zero, hífen invisível e marcas de direção. Imagem gerada e glifo de fonte de ícone (caractere de uso privado) seguem a regra das imagens: conteúdo, salvo com `aria-hidden` | O que aparece legível na tela é conteúdo perceptível; o que não aparece não pode segurar um recorte no placar. Uma contrabarra escapada é contrabarra literal e não abre outro escape. O Chromium só aceita `cross-fade()` com prefixo. |
| O que não é lido | Texto solto do próprio contêiner cortado, elemento com `display: contents` e `::marker` | Declarados no cabeçalho do guard e em [LIMITACOES.md](LIMITACOES.md). |

### GUARD 5 (varredura)

| Ponto | Decisão | Motivo |
|---|---|---|
| Rota não medível | Decidida só pelo status HTTP da resposta principal: 4xx, 5xx ou nenhuma resposta. A rota é registrada sem medição e contada como quebrada | É o que a spec pede. Nenhuma resposta principal também entra: sem status, não há como afirmar que a página é a da rota. Página de erro servida com status 200 não é reconhecida. |
| Saída padrão | `out/medicao` quando `--saida` não é informada; `out/varredura` só por escolha explícita | A spec pede saída configurável para que medir de novo não sobrescreva a baseline fixada. |
| Página da conferência de estado inicial | A primeira rota da própria área | A propriedade conferida vale para o contexto inteiro, e uma rota da matriz existe em qualquer projeto. |
| Área pública no relatório | O parcial registra a área de cada rota; o relatório consolidado não agrupa por área | Separar o relatório por área não foi implementado. |

### GUARD 6 (consolidação)

| Ponto | Decisão | Motivo |
|---|---|---|
| Escopo conferido | `rotas_medidas` e `identificadores_de_detalhe` entram na recusa por escopo divergente | Numa mesma execução, todos os viewports percorrem a mesma lista. |
| Execução vazia | Parciais sem nenhuma rota, ou matriz sem viewport, são `2` | Assinatura vazia de uma execução que mediu nada não prova nada; a do placar zero, com rotas medidas, continua aceita com aviso. |
| Rota não medível na assinatura | Fica **fora** da assinatura; entra no relatório, com o motivo | A spec define a assinatura como a lista dos defeitos de página. A consequência está declarada no cabeçalho do GUARD 6. |
| Identificador da execução | Fica só nos parciais, não no relatório; o resumo cobre relatório e assinatura. O recomendado é um `uuid4` aleatório | A spec exige o identificador nos parciais, e relatório igual byte a byte entre duas medições de uma interface que não mudou; as duas coisas só valem juntas se o relatório não imprimir o identificador. O `uuid4` não se repete e não carrega data nem hora. Custo, declarado no cabeçalho do GUARD 6: os parciais ficam fora do resumo, e `sha256sum -c` não confere a integridade deles. |
