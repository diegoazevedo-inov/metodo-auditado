# Limitações conhecidas

Cada verificador declara, no próprio cabeçalho, em "LIMITAÇÕES DECLARADAS", o
que não cobre e o recurso complementar para essa parte. Aqui ficam os pontos
conhecidos que pedem trabalho, e não só declaração.

## GUARD 4 — texto que o estilo põe na tela

- **Texto do próprio contêiner cortado.** O critério olha só os filhos que
  transbordam. Se um filho decorativo também transborda, o achado sai
  decorativo mesmo com o texto do próprio contêiner cortado — um título longo
  sem quebra ao lado de um ornamento largo, por exemplo. É o caso mais
  provável numa interface real.
- **`counter()`, `counters()`, `open-quote` e `close-quote` não são lidos.** O
  texto que eles põem na tela não mantém o recorte no placar.
- **`display: contents` e `::marker` não são lidos.**
- **Texto com tamanho de fonte zero conta como texto**, como o de cor igual ao
  fundo. Acusa a mais.
- **Glifo fora da área de uso privado** (`•`, `✓`, emoji) com `aria-hidden`
  conta como texto. Coerente com a definição, mas acusa a mais quando o glifo
  é ornamento.

O leitor do texto gerado pelo estilo é o trecho mais delicado do kit. Mudança
nele pede plantio novo em `sweep/prova_sonda.py`, visto vermelho antes do
conserto e verde depois.

## GUARD 2 — catraca

- **Chave com `::` a mais e contagem zero** é aceita em silêncio na baseline.
  É inofensiva: uma contagem zero não esconde dívida.

## GUARD 5 — varredura

- **Página de erro servida com status 200** não é reconhecida como rota não
  medível: a decisão é só pelo status HTTP.
- **O relatório consolidado não separa a área pública** das áreas com sessão;
  só o parcial registra a área de cada rota.

## Provas

- **As provas 5 e 6 medem o servidor que estiver no ar** em
  `FIXTURE_BASE_URL`, e não o da árvore (ver "Provas" no README). Uma prova
  que subisse o próprio servidor tiraria essa dependência.
