# Seis verificadores de qualidade de interface

Verificadores automáticos para interface web: paleta de cores, layout
responsivo, contraste nos dois temas, estouro de conteúdo, varredura em vários
tamanhos de tela e consolidação do resultado num relatório com assinatura
reprodutível.

Cada um tem o mesmo contrato de saída, declara no próprio cabeçalho o que
**não** cobre, e vem com uma prova que planta violações fabricadas e exige que
ele as recuse. Uma aplicação de exemplo (`fixtures/`) exercita tudo, para as
provas rodarem de ponta a ponta.

## Os seis

| # | verificador | onde roda | entrada |
|---|---|---|---|
| 1 | `uiguards.palette` — paleta de cores | estático | código de interface |
| 2 | `uiguards.ratchet` — layout responsivo (catraca) | estático | código + baseline |
| 3 | `uiguards.contrast` — contraste computado | estático | tokens de estilo + tabela de pares |
| 4 | `uiguards.overflow` — estouro por elemento | navegador | página carregada |
| 5 | `sweep/executar.py` — varredura multi-viewport | navegador | matriz de rotas e viewports |
| 6 | `uiguards.consolidate` — consolidação e assinatura | — | parciais da varredura |

## Contrato comum

| código | significado |
|---|---|
| `0` | executei e está limpo |
| `1` | executei e **achei** violação |
| `2` | **não consigo executar** (entrada ausente, malformada, config inválida) |

Todo erro interno inesperado é traduzido para `2`, nunca para `1`: um
verificador quebrado jamais pode passar por base limpa.

**Escape hatch** (verificadores estáticos): comentário
`ui-guard-allow: <motivo>` na própria linha, ou sozinho na linha imediatamente
anterior. Marcador que divide a linha com código isenta só aquela linha. O
escopo é opcional — `ui-guard-allow(responsivo): <motivo>`. Marcador sem
motivo, ou com motivo curto demais, **não isenta nada**.

**Determinismo**: a mesma entrada dá sempre a mesma saída. Cada lista sai numa
ordem estável, de critério explícito, e nenhuma saída leva data ou hora. O
identificador da execução é entrada e fica só nos parciais; por isso, entre
duas execuções independentes de uma interface que não mudou, relatório,
assinatura e `resumos.sha256` se repetem byte a byte.

## Requisitos

- Python 3.13. Os verificadores 1, 2, 3 e 6 usam só a biblioteca padrão.
- Playwright com Chromium, para os verificadores 4 e 5:

  ```bash
  pip install playwright
  python3 -m playwright install chromium
  ```

- As provas são scripts `bash`, testados em Linux (usam `sed -i` e
  `sha256sum` do GNU).

## Uso

Todos os comandos partem da raiz do repositório.

```bash
# 1, 2 e 3 — estáticos
python3 -m uiguards.palette   --config guards.toml
python3 -m uiguards.ratchet   --config guards.toml --modo catraca   # ou estrito | refixar
python3 -m uiguards.contrast  --config guards.toml --pares pares-contraste.toml

# aplicação de exemplo (necessária para 4, 5 e 6)
python3 fixtures/site/servidor.py 8731 &

# 4 — medição avulsa de uma URL (mede; não aprova nem reprova)
python3 -m uiguards.overflow --config guards.toml --url http://127.0.0.1:8731/relatorios

# 5 — a suíte começa pela prova do GUARD 4; se ela reprovar, nada é medido.
#     Medição nova vai para um diretório próprio, nunca para out/varredura.
export FIXTURE_USUARIO=operador FIXTURE_SENHA=senha-de-fixture
ID="$(python3 -c 'import uuid; print(uuid.uuid4())')"
python3 sweep/executar.py --id "$ID" --saida "out/medicao/$ID"

# 6 — consolida, assina e resume; compara com a baseline fixada
python3 -m uiguards.consolidate --parciais "out/medicao/$ID"
(cd "out/medicao/$ID" && sha256sum -c resumos.sha256)
diff out/varredura/assinatura.txt "out/medicao/$ID/assinatura.txt"
```

Credenciais **sempre** por variável de ambiente, nunca embutidas.

O identificador da execução é **fornecido externamente** e tem de ser
**único**. O consolidador recusa identificador ausente, identificadores
diferentes e escopos diferentes (rotas medidas inclusive); dois parciais de
execuções distintas com o **mesmo** identificador e o mesmo escopo passam como
uma execução só. Um `uuid4`, como acima, não se repete e não carrega data nem
hora. O hash do commit **não serve**: ele se repete em toda execução do mesmo
commit.

### Regerar a baseline fixada (`out/varredura/`)

É um passo próprio, feito de propósito, e nunca o efeito colateral de medir:

```bash
export FIXTURE_USUARIO=operador FIXTURE_SENHA=senha-de-fixture
A="$(python3 -c 'import uuid; print(uuid.uuid4())')"
B="$(python3 -c 'import uuid; print(uuid.uuid4())')"
python3 sweep/executar.py --id "$A" --saida "out/medicao/$A"
python3 sweep/executar.py --id "$B" --saida "out/medicao/$B"
python3 -m uiguards.consolidate --parciais "out/medicao/$A"
python3 -m uiguards.consolidate --parciais "out/medicao/$B"
# só com assinatura e relatório iguais nas duas a baseline pode ser dada por fixada
cmp "out/medicao/$A/assinatura.txt" "out/medicao/$B/assinatura.txt" \
  && cmp "out/medicao/$A/relatorio.txt" "out/medicao/$B/relatorio.txt" \
  && rm -rf out/varredura && cp -r "out/medicao/$A" out/varredura \
  && (cd out/varredura && sha256sum -c resumos.sha256)
```

`out/medicao/` é ignorado pelo git; `out/varredura/` é a baseline versionada.

## Provas

Um verificador só é usado depois que um caso fabricado de **cada espécie que
ele detecta** foi posto diante dele e recusado. Cada prova **afirma** o que
espera — código de saída, espécie nomeada, silêncio sobre o que é legítimo — e
devolve `1` quando alguma verificação não fecha.

```bash
proofs/prova_guard1.sh        # 55 verificações: as 9 espécies, escape hatch, importações, configuração
proofs/prova_guard2.sh        # 61 verificações: as 4 regras, catraca para baixo e para cima, os modos, baseline
proofs/prova_guard3.sh        # 36 verificações: violar, corrigir, token ausente, alfa, faixa, informativos
python3 -m sweep.prova_sonda  # 23 testes: as 4 espécies, as isenções, o critério decorativo, texto gerado pelo estilo
proofs/prova_guard5.sh        # 24 verificações: destino, cobertura, estado, detector reprovado, credenciais, matriz
proofs/prova_guard6.sh        # 32 verificações: assinatura reprodutível, recusas, guard de âncora, erros HTTP
proofs/experimento_piso.py    # determinação do piso de severidade por medição
```

As provas restauram tudo que tocam — inclusive sob `Ctrl+C` — e escrevem
apenas em diretório temporário próprio; a do GUARD 6 sobe a aplicação de
exemplo numa porta livre escolhida na hora e a encerra ao sair.

A sonda e as provas 5 e 6 precisam da aplicação de exemplo no ar e de
`FIXTURE_USUARIO`/`FIXTURE_SENHA` definidos. Elas medem a aplicação que
estiver em `FIXTURE_BASE_URL` (por padrão `http://127.0.0.1:8731`), e não o
`fixtures/site/servidor.py` da árvore: depois de alterar o servidor de
exemplo, reinicie-o antes de rodar as provas. Se a porta 8731 estiver ocupada,
suba o servidor em outra e aponte `FIXTURE_BASE_URL` para ela.

## Estrutura

```
uiguards/        common.py  palette.py  ratchet.py  contrast.py
                 overflow.py  overflow_probe.js  consolidate.py
sweep/           prova_sonda.py  varredura.py  executar.py
proofs/          uma prova por verificador + experimento do piso
fixtures/        ui-src/ (alvo estático)  tokens.css  site/servidor.py (aplicação)
out/varredura/   baseline fixada da varredura
guards.toml      configuração dos verificadores
rotas.toml       matriz de rotas e viewports
pares-contraste.toml      tabela de pares + a decisão sobre ornamentais
baseline-responsivo.json  contagem conhecida da catraca
```

## Documentos

| documento | o que é |
|---|---|
| [SPEC.md](SPEC.md) | o que cada verificador tem de fazer, e como se prova |
| [DECISOES.md](DECISOES.md) | as escolhas desta implementação onde a spec deixa em aberto |
| [LIMITACOES.md](LIMITACOES.md) | o que é conhecido e ainda pede trabalho |
