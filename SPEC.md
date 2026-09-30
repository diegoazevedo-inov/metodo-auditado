# SPEC — seis verificadores de qualidade de interface

Esta spec descreve **o quê** cada verificador faz: comportamento observável,
códigos de saída, recusas e o critério de prova que sustenta cada um. Não
descreve **o como**. Linguagem, arquitetura, nomes e mecanismos internos ficam
com quem implementa (última seção). As escolhas desta implementação, nos
pontos que a spec deixa em aberto, estão em [DECISOES.md](DECISOES.md).

---

## Contrato comum a todos os seis

**Códigos de saída — idênticos nos seis, e um CI precisa distinguir os três:**

| | |
|---|---|
| `0` | executei e está limpo |
| `1` | executei e **achei** violação |
| `2` | **não consigo executar** (entrada ausente, malformada, configuração inválida) |

Confundir `2` com `1` é o pior dos três: um verificador quebrado passaria por base
contaminada, e quem investiga desiste no lugar errado.

**Limitações declaradas.** Cada guard deve trazer, no próprio cabeçalho, a relação
honesta do que **a sua implementação** não cobre, escrita por quem a implementou, apontando
o recurso complementar (inspeção visual, outra medição) para aquilo que fica descoberto. A
spec fixa apenas o **mínimo** que cada lista precisa cobrir (indicado em cada guard); o
restante depende das escolhas de implementação.

**Escape hatch.** Exceção legítima é declarada por um marcador em comentário que traga
**o motivo por escrito**. O marcador tem de poder ficar junto da linha isentada (a posição
exata aceita é de quem implementa, mas tem de estar documentada). O formato não deve aceitar
marcador sem motivo.

**Determinismo.** A mesma entrada produz sempre a mesma saída. As listas saem em ordem
definida por critério estável e explícito, e nenhuma saída inclui marca de data ou hora,
seja da execução, seja de qualquer outro evento (a gravação de um arquivo, por exemplo).

**Prova obrigatória.** Nenhum guard entra em uso antes de uma demonstração: para **cada
espécie que ele afirma detectar**, planta-se uma violação fabricada com esse fim e
confirma-se que ele **recusa**. Sem isso não há evidência de que o verificador funciona. As provas de cada
guard estão especificadas adiante e fazem parte da entrega; não são item opcional.

---

# GUARD 1 — Paleta de cores

## Propósito
Impedir que cor literal volte ao código de interface depois que o projeto passou a expressar
as cores do tema por tokens semânticos. Cada literal que entra é um ponto que qualquer tema
adicional terá de corrigir à mão.

## Entrada
- Diretório-raiz do código de interface a varrer.
- Conjunto de extensões de arquivo de componente a considerar.
- Configuração do projeto: nomes das famílias de cor do framework CSS em uso, os prefixos de
  propriedade que aceitam cor, e a correspondência entre cada fundo sólido de papel semântico
  e o token de texto que foi validado sobre ele.
- Allowlist de arquivos isentos, **cada entrada com motivo escrito**. Ela deve ser mantida
  pequena, e o seu tamanho só pode diminuir com o tempo.

## Saída e formato do relatório
Agrupado **por espécie de violação**, e dentro de cada espécie a lista de ocorrências com
arquivo, linha e o trecho exato que disparou. Cada espécie traz uma dica de correção — qual
token usar no lugar. Ao final, total de violações e total de arquivos varridos. Quando limpo,
uma linha declarando quantos arquivos foram varridos e zero violações.

## Regras de decisão
O guard precisa recusar, em arquivos de componente, **pelo menos** as seguintes situações.
Como agrupá-las em espécies (e quantas espécies existem) é de quem implementa, desde que o
relatório nomeie cada situação de forma distinguível e a prova plante uma de cada:

- uso de uma família de cor do framework com grau numérico;
- branco ou preto absolutos aplicados por utilitário, inclusive quando acompanhados de
  modificador de opacidade;
- cor hexadecimal literal;
- notação funcional de cor (RGB, HSL e equivalentes) com valores literais;
- **combinação proibida**: sobre fundo sólido de papel semântico, qualquer cor de texto que
  não coincida **exatamente** com o token de contraste declarado para esse fundo. O único
  texto aceito sobre aquele fundo é o token associado a ele;
- **classe malformada**: dois modificadores de opacidade no mesmo utilitário — classe
  inválida, que na prática não aplica cor nenhuma;
- **cor de marca aplicada como cor de texto** num elemento que exibe texto. Em ícones e
  bordas ela segue permitida; a restrição existe porque, usada como texto, ela tende a ficar
  abaixo do contraste mínimo.

## Casos de borda
- **Notação funcional cujo argumento é referência a variável é o uso correto**, e não pode ser
  acusada. A detecção tem de separar esse caso do literal.
- **Notação funcional embutida em valor maior**: um valor arbitrário do framework pode
  carregar a notação funcional no meio de outros valores, unidos por separador que não é
  espaço. Esse caso **tem de ser acusado**; a prova o planta explicitamente.
- **Duas alternativas de classe na mesma linha** (expressão condicional): quando só uma das
  alternativas carrega o fundo sólido, a outra **não** pode ser acusada de combinação
  proibida. A prova planta esse caso e exige que não acuse.
- **Controle sem rótulo em texto, só com ícone**, fica fora da regra de cor de marca como
  texto: nele a cor pinta o ícone.
- **Variantes de pseudo-elemento que exibem texto** entram na regra de cor de marca como
  texto, mesmo quando aplicadas a um elemento que não é textual.
- **Marcação de várias linhas**: os atributos de um elemento podem ocupar várias linhas, com
  as classes distantes da linha em que o elemento começa. A regra de cor de marca como texto
  tem de alcançar esse caso **quando o elemento contém texto literal**, e **não** pode acusar
  um controle que só tem ícone escrito em várias linhas. A prova planta os dois casos.
- Linhas de importação e de comentário não são avaliadas.

## Aprovação e reprovação
- **Aprova** com zero violações fora da allowlist.
- **Reprova** com qualquer violação, listando-as agrupadas.

## Limitações a declarar no cabeçalho
No mínimo: o que fica fora do escopo varrido e o que a análise **não correlaciona** (por
exemplo, variantes de estado, cor de fundo e cor de texto aplicadas em elementos diferentes,
classes compostas em tempo de execução). O restante da lista depende da técnica escolhida e é
obrigação de quem implementa escrevê-la.

## Como testar
Plantar, em arquivo temporário dentro do escopo varrido:
- **um exemplar de cada situação** listada nas regras de decisão → exigir saída `1`
  **nomeando cada uma**;
- o **uso correto** (referência a variável dentro da notação funcional) → exigir que **não** acuse;
- a **notação funcional embutida em valor maior** → exigir que **acuse**;
- as **duas alternativas na mesma linha** com fundo só numa delas → exigir que **não** acuse
  a outra;
- a **marcação de várias linhas** com texto literal → exigir que **acuse**; sem texto (só
  ícone) → exigir que **não** acuse;
- uma violação **com escape hatch e motivo** → exigir que **não** acuse;
- remover tudo → exigir saída `0`.

---

# GUARD 2 — Layout responsivo (catraca)

## Propósito
Num projeto que já carrega violações de layout conhecidas, garantir que o total não aumente
enquanto elas vão sendo pagas. Exigir zero desde o início não serviria nesse cenário: o gate
reprovaria qualquer mudança até que a dívida inteira fosse quitada.

## Entrada
- Diretório-raiz do código de interface e extensões consideradas.
- Arquivo de baseline com a contagem conhecida de violações.
- Modo de operação: **catraca** (padrão), **estrito** (exige zero) e **re-fixar baseline**.

## Saída e formato do relatório
Em catraca: apenas as violações **novas**, agrupadas por regra, com arquivo, linha e trecho, e
a menção ao escape hatch. Em estrito: todas. Ao final, contagem conhecida, contagem atual e
número de novas.

## Regras de decisão
Quatro causas de estouro horizontal a recusar:

1. **Tabela sem contenção de rolagem** — elemento de tabela que não esteja dentro de algo que
   ofereça rolagem horizontal, nem dentro do componente-padrão de tabela do projeto.
2. **Largura fixa em pixels** declarada como valor arbitrário. Declarações de largura máxima
   ou mínima ficam fora da regra.
3. **Impedimento de quebra de linha em célula de conteúdo de tamanho imprevisível** (texto
   livre). A proibição não vale para células de cabeçalho de tabela nem para células cujo
   conteúdo tem comprimento limitado por natureza (status, data, número).
4. **Truncamento sem exposição do valor íntegro** — texto cortado cujo valor completo não
   esteja disponível por atributo acessível.

## A catraca — comportamento central deste guard
- **Granularidade da contagem: por arquivo e por regra.** Comportamento exigido e provado:
  mudar violações de posição dentro de um arquivo (linhas inseridas ou apagadas ao redor,
  ordem trocada), sem alterar quantas ele tem, **não** reprova; acrescentar uma violação a um
  arquivo reprova **mesmo que** outro arquivo tenha perdido uma. Como a contagem é
  representada é de quem implementa.
- Contagem **acima** da baseline, em qualquer arquivo e regra, reprova.
- Contagem **abaixo** da baseline obriga a re-fixar a baseline **no mesmo commit** que
  reduziu a dívida. Do contrário, violações novas poderiam ocupar mais tarde o lugar das
  corrigidas, e o guard não perceberia. Nessa situação o guard reprova e a mensagem diz como
  re-fixar; rodando como gate, ele **nunca** altera a baseline sozinho — re-fixar é sempre um
  comando explícito de quem reduziu a dívida.
- No modo **estrito**, qualquer violação reprova (zero absoluto). Concluída a migração, é ele
  que fica como gate, no lugar da catraca.

## Casos de borda
- Como determinar se a tabela está contida é de quem implementa. A rolagem fornecida por um
  componente cujo código mora fora do arquivo da tabela fica invisível para quem lê só esse
  arquivo; por isso o componente-padrão de tabela do projeto tem de ser identificável
  diretamente (o nome é um critério possível), sem depender de achar a propriedade de
  rolagem. Aceitar **só** o componente-padrão e dispensar qualquer inferência é alternativa
  válida.
- O arquivo que **define** o componente-padrão de tabela é isento da regra 1.
- Na regra 4, o atributo acessível pode estar em outra linha da mesma tag; esse caso tem de
  ser alcançado e é plantado na prova.
- Comentários não são avaliados.

## Aprovação e reprovação
- **Catraca:** aprova com zero novas **e** nenhuma contagem reduzida sem re-fixação.
- **Estrito:** aprova apenas com zero absoluto.
- Baseline ausente é `2`, não `1`: não consigo executar.

## Limitações a declarar
No mínimo: que nada é medido em tempo de execução — medir a tela é papel dos GUARDS 4–6 — e
o que a análise não enxerga (conteúdo variável fora do alcance da regra 3; classes montadas
dinamicamente).

## Como testar
- Plantar **uma violação de cada uma das quatro regras** → exigir `1`, com as quatro regras
  identificadas no relatório.
- Modo estrito sobre base com dívida → exigir `1`; sobre base limpa → exigir `0`.
- **Provar que a catraca cobra as duas direções**: partir de uma baseline conhecida;
  **reduzir** a dívida e exigir que o guard **reprove pedindo re-fixação**; re-fixar; depois
  **aumentar** de novo até a contagem anterior e exigir que **reprove**.
- **Provar a granularidade**: mudar violações de posição dentro de um arquivo sem alterar sua
  contagem → exigir `0`; acrescentar uma violação num arquivo enquanto outro perde uma →
  exigir `1`.
- Plantar a regra 4 com o atributo acessível **em outra linha da mesma tag** → exigir que
  **não** acuse.
- Plantar uma violação **com escape hatch** → exigir que não acuse.

---

# GUARD 3 — Contraste computado

## Propósito
Fazer com que a legibilidade dos pares de cor seja decidida por cálculo contra a norma, e não
por inspeção visual. Um par pode parecer adequado na tela e mesmo assim ficar abaixo do
mínimo exigido.

## Entrada
- Arquivo de estilo global contendo **dois blocos de tokens de cor**: o tema base e o tema
  alternativo.
- Tabela de pares a avaliar. Para cada par, o guard precisa saber qual token é a frente, qual
  é o fundo, qual a razão mínima exigida, como rotulá-lo no relatório e se ele é
  **informativo**. A forma da tabela é de quem implementa.

## Saída e formato do relatório
Uma seção por tema. Dentro dela, uma linha por par com a razão calculada, o mínimo exigido, o
rótulo e o veredito. Pares informativos aparecem marcados como tal. Ao final de cada tema, a
contagem de reprovações e quantos pares eram avaliados contra quantos eram informativos.

## Regras de decisão
- Localizar cada bloco de tokens pelo seu seletor. Comportamento exigido e provado: uma
  menção ao seletor **fora** de um bloco (em comentário, por exemplo) não pode ser tomada como
  o bloco; e um bloco que contenha chaves aninhadas tem de ser lido inteiro.
- O tema alternativo é avaliado com os valores do tema base para todo token que ele **não
  sobrescreve**: a avaliação é feita sobre a união, não sobre o bloco isolado.
- Converter o valor de cor declarado para luminância relativa e calcular a razão de contraste
  conforme a norma de acessibilidade vigente.
- **Mínimos:** texto corrente exige a razão maior; elemento de interface, indicador de foco e
  texto de dica exigem a razão menor. Os dois valores vêm da norma, não de escolha do projeto.
- **Pares informativos**: combinações que o projeto decidiu **não** usar e que permanecem na
  tabela para que a razão medida fique registrada. Reprovam quando calculadas, mas **não
  derrubam o gate**. Funcionam como registro da decisão tomada.

## Casos de borda
- **Token ausente reprova**, e nunca passa por omissão — salvo se o par for informativo.
- Valor de cor em formato inesperado é `2` (não consigo calcular), nunca aprovação.
- Bloco de tokens não encontrado é `2`.
- Tratar como informativos os pares de bordas e de cores de destaque que sejam só ornamento
  é **OPCIONAL**; é decisão de projeto e deve ficar registrada junto da tabela.

## Aprovação e reprovação
Aprova com zero reprovações **entre os pares avaliados**, nos dois temas. Pares informativos
reprovando não impedem a aprovação — mas devem aparecer no relatório.

## Como testar
- Ajustar um token de modo a **violar** um par avaliado → exigir `1` **nomeando o par**.
- Corrigir o valor → exigir `0`.
- **Remover um token** referenciado por um par avaliado → exigir reprovação por ausência
  (nunca aprovação silenciosa).
- Apontar para um arquivo sem os blocos esperados → exigir `2`.
- Inserir, **antes** do bloco real, um comentário que mencione o seletor → exigir que o guard
  leia o bloco real.
- Confirmar que um par **informativo** reprovando **não** derruba o gate.

---

# GUARD 4 — Detector de estouro por elemento

Este e os dois seguintes formam o trio de medição. Rodam dentro de um navegador automatizado.

## Propósito
Apontar, na página já renderizada, os elementos que têm conteúdo mais largo do que o espaço
horizontal que oferecem. O resultado é por **elemento**; uma métrica agregada da página
não o substitui.

## Entrada
Uma página já carregada, com o layout estável. Limitar a quantidade de itens reportados é
**OPCIONAL**.

## Saída
As métricas da página e os achados por espécie. Cada achado precisa permitir: **reencontrar**
o elemento (um identificador legível e curto), **quantificar** o excesso (quanto o conteúdo
mede, quanto cabe, quanto sobra) e saber a **espécie**. Quando vários elementos aninhados
acusam o mesmo excesso, o relatório tem de permitir saber **qual deles corrigir** (o mais
profundo entre os que acusam, ou o filho que provoca o excesso); a forma de indicar isso é de
quem implementa.

## Regras de decisão
- Um elemento é candidato quando a largura do seu conteúdo excede a largura visível **além de
  um piso de severidade**.
- **A classificação considera apenas como o próprio elemento trata o excesso horizontal; o
  que os ancestrais fazem fica fora da decisão.** Esta é a decisão central do guard. Motivo,
  que o cabeçalho deve explicar com as próprias palavras de quem implementa: pelas regras de
  CSS, um contêiner que declara rolagem **vertical** passa a admitir rolagem também no eixo
  horizontal. Se a pergunta fosse sobre os ancestrais, todo elemento abaixo de um contêiner
  assim seria tratado como contido, e estouros reais sumiriam da medição. A prova deste guard
  planta exatamente esse caso.
- **Quatro espécies:** o conteúdo passa visivelmente dos limites da caixa; parte do conteúdo
  fica escondida pelo corte e **nenhuma** rolagem dá acesso a ela; o corte esconde **somente
  decoração**; e há rolagem horizontal que a classe do elemento **não** declara.
- **O placar é formado por três espécies: a do conteúdo que passa visivelmente da caixa, a
  do conteúdo escondido sem rolagem e a da rolagem horizontal não declarada.** A espécie
  decorativa é **excluída** dessa contagem e listada separadamente, de modo que elementos
  sem dano visível não aumentem o placar.
- **Critério da espécie decorativa — comportamento exigido:** um recorte só é decorativo se
  **nada** do que ele esconde for conteúdo perceptível ou interativo para quem usa; havendo
  qualquer conteúdo entre o que foi escondido, a espécie é a de recorte real. Se não for
  possível determinar o que está sendo escondido, vale a opção **conservadora**: o achado
  permanece no placar. Quais sinais do DOM e do estilo computado são usados para decidir
  "decoração" é de quem implementa, e a prova planta um caso de cada lado.

## Casos de borda e isenções
- Quando a classe declara **rolagem horizontal**, o excesso é esperado e não gera achado.
- Quando a classe declara **truncamento**, o corte é proposital e não gera achado. **Essa
  isenção não vale para o truncamento declarado só a partir de um ponto de quebra**: abaixo
  dessa largura a declaração não tem efeito, e as larguras estreitas são as que mais
  interessam à varredura.
- Conteúdo escondido na tela mas exposto a leitores de tela não gera achado: esse recurso
  funciona, de propósito, espremendo o conteúdo num espaço ínfimo.
- Elementos internos de um **gráfico vetorial** não são medidos; o elemento raiz do gráfico é
  medido normalmente, como qualquer outro participante do layout.
- Não são medidos elementos **sem renderização** nem caixas de **dimensão desprezível**.
- **Piso de severidade:** excessos muito pequenos são ruído do próprio motor de renderização,
  variam de uma execução para outra e, se contados, impediriam que duas medições do mesmo
  estado coincidissem. A spec **exige que exista um piso e que ele seja justificado por
  medição**; o valor numérico é **OPCIONAL**, e cada projeto chega ao seu confrontando duas
  varreduras completas. Elementos abaixo do piso **não** são reportados; os que ficam acima
  aparecem com o valor exato medido.
- A lista de achados sai **sempre na mesma ordem**, definida por critério explícito que
  inclua o desempate. Isso é obrigatório.

## Aprovação e reprovação
O detector **não aprova nem reprova** — ele mede. O veredito pertence ao consolidador.

## Como testar — o que sustenta este guard
Manipulando a página e relendo o detector:
- plantar dentro de contêiner com **rolagem vertical** → exigir que **acuse**. Esta é a prova
  central da decisão de classificação;
- plantar dentro de contêiner com **rolagem horizontal declarada** → exigir que **não** acuse;
- plantar **recorte de conteúdo** → exigir a espécie de recorte real;
- plantar **recorte de pura decoração** → exigir a espécie decorativa, e exigir que **não**
  apareça no placar;
- plantar **truncamento declarado** → exigir que **não** acuse;
- plantar truncamento com **variante condicionada a ponto de quebra**, numa largura em que a
  variante não tem efeito → exigir que **acuse**;
- plantar um elemento largo **sem contenção** → exigir que o achado **aponte esse elemento
  pelo identificador**; o total de achados aumentar não serve de prova;
- **retirá-lo** e exigir que ele saia dos achados. O que se confere é a **presença do
  elemento plantado**, e **não** se o total voltou ao valor anterior: a página pode ter casos
  próprios perto do piso, que aparecem numa leitura e somem na seguinte.

Depois de cada alteração, o detector é consultado de novo **até o resultado esperado
aparecer**, com prazo máximo, e não depois de uma pausa de duração fixa: com a máquina
ocupada, uma pausa fixa faz a própria prova falhar só de vez em quando.

---

# GUARD 5 — Varredura como especificação executável

## Propósito
Tornar a medição de estouro um teste permanente do projeto, capaz de servir de gate, e
garantir que a baseline que ela produz se reproduza de uma execução para outra.

## Entrada
- Matriz de rotas, organizada por área, e matriz de viewports.
- Credenciais de acesso **por variável de ambiente**, nunca embutidas.
- Identificador único da execução, fornecido externamente.
- Diretório de saída configurável, para que medir de novo não sobrescreva uma baseline já
  fixada.

## Saída
**Um arquivo parcial por viewport**, contendo os registros medidos, o identificador da execução
e o escopo aplicado. Capturas de tela apenas das rotas com achado, para revisão humana.

## Regras de decisão
- **Cada viewport grava o seu parcial de forma independente**, de modo que a interrupção de
  um viewport (por tempo limite ou erro) não perca a medição dos demais. Juntar os parciais é
  tarefa do GUARD 6.
- **Medição estabilizada:** a página é lida mais de uma vez, e uma leitura só é aceita quando
  o **conjunto de defeitos que contam no placar** deixa de variar de uma leitura para a
  seguinte. O critério é o conjunto (espécie + elemento), **não** as magnitudes: diferenças de
  fração de pixel entre leituras não deixariam o resultado se firmar. Quantas leituras e qual
  a janela de tempo são de quem implementa. Se não houver estabilidade dentro da janela, o
  registro é marcado como **instável**, e o relatório **informa quantos** ficaram assim.
- **Antes de medir:** aguardar que os recursos capazes de terminar de carregar depois da
  página e alterar as dimensões dos elementos (fontes, imagens) estejam prontos. A espera é
  condicionada a esses recursos, não a um tempo escolhido de antemão.
- **Emular preferência por movimento reduzido**, para que a largura lida não dependa do
  instante em que a leitura acontece.
- **Validação de destino:** terminada a navegação, conferir que o endereço final é o pedido.
  Se não for, o **teste falha** e nada é gravado para aquela rota. Sem essa conferência, uma
  sessão vencida ou um redirecionamento faria a medição de uma página ser registrada em nome
  de outra.
- **Navegação lenta não é redirecionamento:** antes de concluir que o destino está errado,
  tentar de novo, com espera. O que é só demora se resolve nessas tentativas; o destino que
  continua errado depois delas é falha.
- **Páginas de detalhe:** o viewport usado para descobrir quais registros abrir é sempre o
  mesmo, e os identificadores obtidos nele valem para todos os viewports. Se cada viewport
  escolhesse os seus, nada garantiria que todos medissem as mesmas páginas, e comparar um
  viewport com outro perderia o sentido.
- **Estado inicial verificável:** quando o teste fixa um modo de exibição por configuração, ele
  deve **confirmar que o modo foi de fato aplicado**, medindo a propriedade resultante na
  página, e **abortar alto** se não foi. Configuração aceita em silêncio produz baseline verde
  medida no estado errado — e duas execuções concordam entre si, o que torna o erro invisível.

## Casos de borda
- O parcial lista, cada uma com o motivo, as rotas que o projeto decidiu deixar fora da
  medição.
- Medir também numa largura extra, mais estreita, voltada às telas pensadas para uso no
  celular, é **OPCIONAL**; adotá-la ou não, e em que telas, cabe ao projeto, e a escolha deve
  ficar registrada.
- Páginas abertas ao público são medidas **sem sessão** e reportadas numa área separada.

## Aprovação e reprovação
A varredura falha quando: uma rota não chega ao destino esperado; a cobertura de páginas de
detalhe fica, sem aviso, menor que o conjunto esperado; ou o estado inicial não foi aplicado.
Ela **não** falha por encontrar defeitos — encontrá-los é a função.

## Como testar
**Esta suíte** executa primeiro a prova do GUARD 4 e só então a varredura, para que nenhuma
baseline venha de um detector que não passou pela prova.

---

# GUARD 6 — Consolidação e assinatura

## Propósito
Juntar os parciais, produzir o relatório e — o ponto central — produzir a **prova de
reprodutibilidade** da medição.

## Entrada
Diretório contendo os parciais esperados, um por viewport.

## Saída
Relatório completo, ranking por módulo, a assinatura e os resumos criptográficos. Como isso
se distribui em arquivos é de quem implementa, desde que a assinatura e os resumos sejam
conferíveis com a ferramenta padrão do sistema.

## Regras de decisão
- **Recusar** (`2`) se **faltar** qualquer parcial esperado: sem todos os viewports, não se
  gera relatório.
- **Recusar** se os parciais declararem **identificadores de execução diferentes** — o
  resultado combinaria medições de execuções distintas.
- **Recusar também o identificador ausente.** Parciais sem identificador seriam
  indistinguíveis entre si; aceitá-los permitiria de novo combinar execuções diferentes sem
  que a recusa anterior as detectasse.
- **Duas execuções são comparadas pela ASSINATURA**: a lista ordenada dos defeitos **de
  página**, cada um identificado por viewport, rota, espécie e elemento. Ela **não** traz
  nenhum texto lido da tela, nem data ou hora, nem magnitude. Motivo: esses três dados mudam
  de uma execução para outra mesmo quando a interface está igual; o que tem de se manter é
  quais defeitos existem.
- **A baseline só é considerada fixada** depois que **duas execuções independentes** chegam à
  mesma assinatura.
- O resumo criptográfico é calculado sobre o arquivo **byte a byte, tal como está em disco**,
  de modo que a ferramenta padrão de conferência do sistema, aplicada ao arquivo, confirme o
  resumo sem nenhum ajuste.
- **Separar defeito de estrutura compartilhada (moldura) de defeito de página.** Um problema
  na moldura se repete em cada rota que a exibe; se não fosse separado, uma única correção
  pendente apareceria multiplicada pelo número de rotas e distorceria o ranking. A separação
  tem de se apoiar numa **marcação semântica posta no layout raiz e desvinculada de estilo**;
  assim, mudanças de aparência não afetam a classificação. O mecanismo de marcação (quantos
  marcadores, onde, como se combinam) é de quem implementa e deve ficar documentado.
- **Guard de marcação:** se há defeitos e a marcação declarada não corresponde a **nenhum**
  deles onde deveria corresponder, **recusar**. É o sintoma de uma marcação renomeada ou
  removida, que de outro modo corromperia a classificação sem deixar rastro. **Com o placar
  zerado, esse guard não é aplicado, e o consolidador emite um aviso dizendo isso**: sem
  defeitos, a classificação não tem objeto, e uma assinatura vazia é exatamente o que se
  espera de um projeto sem estouros. Deixar de aplicá-lo não oculta defeito algum, já que a
  marcação só influi na classificação dos defeitos encontrados, e não em quais são
  encontrados.
- **O ranking por módulo considera somente defeitos de página**; os da moldura ficam fora
  dele, porque corrigi-los é uma tarefa só.
- **O relatório segue o contrato de determinismo** — nenhuma data ou hora, todas as listas em
  ordem estável. Assim, duas medições de uma interface que não mudou produzem arquivos iguais
  byte a byte, e o resumo criptográfico é a prova dessa igualdade.

## Casos de borda
- A contagem de registros **instáveis** vai ao relatório, visível.
- Uma rota que não pôde ser medida, por qualquer motivo, é contada como **quebrada**, e nunca
  como rota em ordem. Isso inclui a rota cujo próprio endereço responde com erro (status HTTP
  4xx ou 5xx, um 404 por exemplo): a página de erro que vem no lugar renderiza e pode ser
  medida, mas não é a página da rota.
- O comando sugerido em qualquer mensagem de erro deve **de fato existir e funcionar** — uma
  instrução impressa exatamente quando a medição falhou não pode ser inválida.

## Aprovação e reprovação
Aprova produzindo relatório, assinatura e resumos. Reprova (`2`) em parcial ausente, mistura
de execuções, identificador ausente ou marcação obsoleta com defeitos presentes.

## Como testar
- Executar **duas vezes** sem mudar nada entre as execuções e exigir **assinatura idêntica** —
  é a prova de reprodutibilidade.
- **Remover um parcial** → exigir `2`.
- **Alterar o identificador** de um parcial → exigir `2`.
- Executar **sem identificador** → exigir `2`.
- Com defeitos presentes, **renomear a marcação** no layout → exigir recusa.
- Com placar **zero**, confirmar que o guard de marcação **deixa de ser aplicado, com aviso**,
  e que a assinatura vazia é aceita.
- Conferir o resumo criptográfico com a ferramenta padrão do sistema e exigir que feche.

---

## O que esta spec deliberadamente NÃO determina

Linguagem, organização de arquivos, nomes de função e variável, formato interno das estruturas
de dados, unidade de análise textual, técnica de inferência de estrutura, predicados internos
de classificação, mecanismo de marcação do layout, biblioteca de automação de navegador, estilo
de mensagem no terminal, redação dos cabeçalhos e estratégia de testes. Tudo isso é de quem
implementa. A spec fixa **comportamento observável e critério de prova** — nada além disso.
