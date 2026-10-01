#!/usr/bin/env bash
# PROVA DO GUARD 3 -- violar um par avaliado, corrigir, remover um token,
# apontar para arquivo sem blocos, formato de cor inesperado, confirmar que
# par informativo reprovando NAO derruba o gate, e as recusas de bloco
# ambiguo: seletor so aninhado em regra-arroba, dois blocos no topo, e regra
# aninhada DENTRO do bloco do tema. Por fim, as duas entradas que ja
# aprovaram par ilegivel: a ultima declaracao sem ';' e a cor com alfa.
#
# Cada verificacao afirma o que espera; o script devolve 1 se alguma nao
# fechar. O arquivo de tokens do projeto e restaurado no trap, inclusive sob
# interrupcao.
set -u
cd "$(dirname "$0")/.."
G="python3 -m uiguards.contrast --config guards.toml"
CSS="fixtures/tokens.css"
TMP="$(mktemp -d)"
cp "$CSS" "$TMP/tokens.bak"
trap 'exit 130' INT TERM
trap 'cp "$TMP/tokens.bak" "$CSS"; rm -rf "$TMP"' EXIT
OUT="$TMP/saida.txt"

FALHAS=0
VERIFICACOES=0
exigir_exit() {
  VERIFICACOES=$((VERIFICACOES + 1))
  if [ "$2" = "$1" ]; then echo "  [ok] $3: EXIT=$2"
  else echo "  [** FALHOU **] $3: EXIT=$2, esperava $1"; FALHAS=$((FALHAS + 1)); fi
}
exigir_texto() {   # exigir_texto <padrao> <rotulo>
  VERIFICACOES=$((VERIFICACOES + 1))
  if grep -q -- "$1" "$OUT"; then echo "  [ok] $2"
  else echo "  [** FALHOU **] $2: nao achei '$1' na saida"; FALHAS=$((FALHAS + 1)); fi
}
# monta um guards.toml apontando para outro arquivo de estilo
cfg_para() {
  sed "s|arquivo_estilo = \"fixtures/tokens.css\"|arquivo_estilo = \"$1\"|" guards.toml > "$TMP/cfg.toml"
  echo "$TMP/cfg.toml"
}

echo "===== (a) ESTADO LIMPO -> 0, e par informativo reprovando NAO derruba o gate ====="
$G > "$OUT" 2>&1; rc=$?
grep -E "INFORMATIVO|reprovacoes no gate|LIMPO" "$OUT"
exigir_exit 0 "$rc" "base limpa"
exigir_texto "INFORMATIVO" "par informativo aparece no relatorio"
# Nao basta a palavra: o par informativo tem de estar REPROVANDO nesta saida,
# senao o "nao derruba o gate" acima nao foi exercitado.
exigir_texto "reprova (nao derruba o gate) \[INFORMATIVO\]" \
  "um par informativo reprova na saida, e mesmo assim o gate fica em 0"

echo
echo "===== (b) VIOLAR UM PAR AVALIADO: --muted-foreground clareado no tema base ====="
sed -i '0,/--muted-foreground: 215 16% 40%;/s||--muted-foreground: 215 16% 66%;|' "$CSS"
$G > "$OUT" 2>&1; rc=$?; grep -E "REPROVA|TOTAL" "$OUT"
exigir_exit 1 "$rc" "par avaliado violado reprova"
exigir_texto "texto secundario sobre o fundo da pagina" "a saida nomeia o par que reprovou"

echo
echo "===== (c) CORRIGIR O VALOR -> 0 ====="
cp "$TMP/tokens.bak" "$CSS"
$G > "$OUT" 2>&1; rc=$?; tail -1 "$OUT"
exigir_exit 0 "$rc" "valor corrigido volta a passar"

echo
echo "===== (d) REMOVER UM TOKEN REFERENCIADO POR PAR AVALIADO -> reprova por ausencia ====="
echo "      (--ring some dos DOIS blocos; nunca pode passar por omissao)"
sed -i '/--ring:/d' "$CSS"
$G > "$OUT" 2>&1; rc=$?; grep -E "TOKEN AUSENTE|TOTAL" "$OUT"
exigir_exit 1 "$rc" "token ausente reprova"
exigir_texto "TOKEN AUSENTE" "a saida nomeia o token que falta"
cp "$TMP/tokens.bak" "$CSS"

echo
echo "===== (e) ARQUIVO SEM OS BLOCOS ESPERADOS -> 2, nao 1 ====="
printf '/* so um comentario mencionando :root e .dark, sem bloco nenhum */\nbody { margin: 0; }\n' > "$TMP/sem-blocos.css"
python3 -m uiguards.contrast --config "$(cfg_para "$TMP/sem-blocos.css")" \
  --pares pares-contraste.toml > "$OUT" 2>&1; rc=$?; cat "$OUT"
exigir_exit 2 "$rc" "arquivo sem blocos e 'nao consigo executar'"
echo "      ^ o :root citado no comentario NAO foi tomado como bloco"

echo
echo "===== (f) FORMATO DE COR INESPERADO -> 2, nao consigo calcular ====="
sed -i 's|--foreground: 222 47% 11%;|--foreground: var(--outra-coisa);|' "$CSS"
$G > "$OUT" 2>&1; rc=$?; cat "$OUT"
exigir_exit 2 "$rc" "formato de cor inesperado"
cp "$TMP/tokens.bak" "$CSS"

echo
echo "===== (g) O BLOCO DO TEMA SO EXISTE ANINHADO EM @media -> 2, nunca aprovacao ====="
python3 - "$TMP/so-aninhado.css" <<'PY'
import pathlib, sys
css = pathlib.Path("fixtures/tokens.css").read_text()
raiz, escuro = css.split("\n.dark {")
pathlib.Path(sys.argv[1]).write_text(
    raiz + "\n@media (prefers-color-scheme: dark) {\n.dark {" + escuro + "\n}\n")
PY
python3 -m uiguards.contrast --config "$(cfg_para "$TMP/so-aninhado.css")" \
  --pares pares-contraste.toml > "$OUT" 2>&1; rc=$?; head -3 "$OUT"
exigir_exit 2 "$rc" "seletor do tema so aninhado em regra-arroba"

echo
echo "===== (h) BLOCO EM @media ANTES DO BLOCO REAL -> le o REAL, e o real reprova ====="
echo "      (o @media repete o tema claro; o .dark verdadeiro tem 1,08:1 -- texto invisivel)"
python3 - "$TMP/media-antes.css" <<'PY'
import pathlib, sys
css = pathlib.Path("fixtures/tokens.css").read_text()
raiz, escuro = css.split("\n.dark {")
media = ("\n@media (prefers-color-scheme: dark) {\n  .dark {\n"
         "    --background: 0 0% 100%;\n    --foreground: 222 47% 11%;\n  }\n}\n")
real = ".dark {" + escuro.replace("--foreground: 210 40% 96%;", "--foreground: 222 47% 12%;")
pathlib.Path(sys.argv[1]).write_text(raiz + media + "\n" + real)
PY
python3 -m uiguards.contrast --config "$(cfg_para "$TMP/media-antes.css")" \
  --pares pares-contraste.toml > "$OUT" 2>&1; rc=$?
grep -E "1.08|REPROVA|TOTAL" "$OUT" | head -3
exigir_exit 1 "$rc" "o bloco lido e o que aplica na tela"
exigir_texto "1.08:1" "a razao calculada e a do bloco real"

echo
echo "===== (i) REGRA ANINHADA DENTRO DO BLOCO DO TEMA NAO SUBSTITUI O TOKEN ====="
echo "      (nesting nativo: o que aplica no seletor e a declaracao de topo)"
python3 - "$TMP/nesting.css" <<'PY'
import pathlib, sys
css = pathlib.Path("fixtures/tokens.css").read_text()
raiz, escuro = css.split("\n.dark {")
real = ".dark {" + escuro.replace(
    "--foreground: 210 40% 96%;",
    "--foreground: 222 47% 12%;\n  .legado { --foreground: 210 40% 96%; }")
pathlib.Path(sys.argv[1]).write_text(raiz + "\n" + real)
PY
python3 -m uiguards.contrast --config "$(cfg_para "$TMP/nesting.css")" \
  --pares pares-contraste.toml > "$OUT" 2>&1; rc=$?
grep -E "1.08|REPROVA|TOTAL" "$OUT" | head -3
exigir_exit 1 "$rc" "a declaracao aninhada nao esconde a de topo"
exigir_texto "1.08:1" "a razao medida e a que aplica no seletor"

echo
echo "===== (j) DOIS BLOCOS DO MESMO TEMA NO TOPO -> 2, o guard nao adivinha ====="
python3 - "$TMP/dois-blocos.css" <<'PY'
import pathlib, sys
css = pathlib.Path("fixtures/tokens.css").read_text()
pathlib.Path(sys.argv[1]).write_text(css + "\n.dark {\n  --foreground: 222 47% 12%;\n}\n")
PY
python3 -m uiguards.contrast --config "$(cfg_para "$TMP/dois-blocos.css")" \
  --pares pares-contraste.toml > "$OUT" 2>&1; rc=$?; head -2 "$OUT"
exigir_exit 2 "$rc" "dois blocos de topo para o mesmo tema"

# Tabela de um par so, para os plantios com tokens proprios (k) a (m).
cat > "$TMP/pares-fg-bg.toml" <<'TOML'
[[par]]
frente = "--fg"
fundo = "--bg"
minimo = "texto"
rotulo = "par plantado fg sobre bg"
informativo = false
TOML

echo
echo "===== (k) ULTIMA DECLARACAO SEM ';' -> e lida, e o par real (1,11:1) reprova ====="
echo "      (o CSS permite omitir o ';' da ultima declaracao; perder --bg faria"
echo "       o tema alternativo herdar o #ffffff do base e aprovar a 18,88:1)"
printf ':root { --fg: #111111; --bg: #ffffff; }\n.dark { --fg: #111111; --bg: #000000 }\n' > "$TMP/sem-ponto-virgula.css"
python3 -m uiguards.contrast --config "$(cfg_para "$TMP/sem-ponto-virgula.css")" \
  --pares "$TMP/pares-fg-bg.toml" > "$OUT" 2>&1; rc=$?
grep -E ":1 |TOTAL|LIMPO" "$OUT"
exigir_exit 1 "$rc" "ultima declaracao sem ';' nao some"
exigir_texto "1.11:1 .*REPROVA .*par plantado fg sobre bg" "a saida nomeia o par e a razao real"
echo "  -- vizinho legitimo: a mesma forma, com par legivel, passa"
printf ':root { --fg: #111111; --bg: #ffffff; }\n.dark { --fg: #eeeeee; --bg: #000000 }\n' > "$TMP/sem-ponto-virgula-ok.css"
python3 -m uiguards.contrast --config "$(cfg_para "$TMP/sem-ponto-virgula-ok.css")" \
  --pares "$TMP/pares-fg-bg.toml" > "$OUT" 2>&1; rc=$?
grep -E ":1 |TOTAL|LIMPO" "$OUT"
exigir_exit 0 "$rc" "ultima declaracao sem ';' com par legivel passa"
echo "  -- e o bloco sem a chave que o fecha continua recusado"
printf ':root { --fg: #111111; --bg: #ffffff; }\n.dark { --fg: #111111; --bg: #000000\n' > "$TMP/sem-fechamento.css"
python3 -m uiguards.contrast --config "$(cfg_para "$TMP/sem-fechamento.css")" \
  --pares "$TMP/pares-fg-bg.toml" > "$OUT" 2>&1; rc=$?; cat "$OUT"
exigir_exit 2 "$rc" "bloco sem fechamento balanceado"

echo
echo "===== (l) COR COM ALFA ABAIXO DE 1 -> 2, nomeando o token ====="
echo "      (a cor efetiva depende do que esta atras; nao se calcula, e nao se aprova)"
sed -i '0,/--foreground: 222 47% 11%;/s||--foreground: rgba(0, 0, 0, 0.15);|' "$CSS"
$G > "$OUT" 2>&1; rc=$?; cat "$OUT"
exigir_exit 2 "$rc" "rgba() com alfa fracionario"
exigir_texto "alfa.*--foreground" "a recusa nomeia o alfa e o token"
cp "$TMP/tokens.bak" "$CSS"
sed -i '0,/--foreground: 222 47% 11%;/s||--foreground: rgb(0 0 0 / 15%);|' "$CSS"
$G > "$OUT" 2>&1; rc=$?; cat "$OUT"
exigir_exit 2 "$rc" "alfa depois de '/', em porcentagem"
cp "$TMP/tokens.bak" "$CSS"
echo "  -- vizinho legitimo: alfa exatamente 1 e opaco e segue calculado"
sed -i '0,/--foreground: 222 47% 11%;/s||--foreground: rgba(0, 0, 0, 1);|' "$CSS"
$G > "$OUT" 2>&1; rc=$?; grep -E "texto corrente|LIMPO|TOTAL" "$OUT"
exigir_exit 0 "$rc" "rgba() com alfa 1 e opaco"
cp "$TMP/tokens.bak" "$CSS"

echo
echo "===== (m) COMENTARIO COM FORMA DE BLOCO ANTES DO BLOCO REAL -> le o REAL ====="
echo "      (o comentario traz um .dark legivel; o .dark real tem 1,11:1. Lido o"
echo "       comentario, o guard veria dois blocos, ou aprovaria o par errado)"
printf ':root { --fg: #111111; --bg: #ffffff; }\n/* .dark { --fg: #eeeeee; --bg: #000000; } */\n.dark { --fg: #111111; --bg: #000000; }\n' > "$TMP/comentario-bloco.css"
python3 -m uiguards.contrast --config "$(cfg_para "$TMP/comentario-bloco.css")" \
  --pares "$TMP/pares-fg-bg.toml" > "$OUT" 2>&1; rc=$?
grep -E ":1 |TOTAL|LIMPO|CONSIGO" "$OUT"
exigir_exit 1 "$rc" "o bloco comentado nao e lido"
exigir_texto "1.11:1 .*REPROVA .*par plantado fg sobre bg" "a razao e a do bloco real"

echo
echo "===== (n) VALOR DE COR FORA DA FAIXA -> 2, nunca uma razao inflada ====="
echo "      (#ffffff sobre #777777 da 4,48:1; rgb(300,300,300) daria 6,40:1 e aprovaria)"
printf ':root { --fg: rgb(300, 300, 300); --bg: #777777; }\n.dark { --fg: #ffffff; --bg: #777777; }\n' > "$TMP/fora-rgb.css"
python3 -m uiguards.contrast --config "$(cfg_para "$TMP/fora-rgb.css")" \
  --pares "$TMP/pares-fg-bg.toml" > "$OUT" 2>&1; rc=$?; cat "$OUT"
exigir_exit 2 "$rc" "rgb acima de 255"
exigir_texto "fora da faixa .*--fg" "a recusa nomeia a faixa e o token"
printf ':root { --fg: 0 0%% 150%%; --bg: 0 0%% 47%%; }\n.dark { --fg: #ffffff; --bg: #777777; }\n' > "$TMP/fora-hsl.css"
python3 -m uiguards.contrast --config "$(cfg_para "$TMP/fora-hsl.css")" \
  --pares "$TMP/pares-fg-bg.toml" > "$OUT" 2>&1; rc=$?; cat "$OUT"
exigir_exit 2 "$rc" "tripla HSL com luminosidade acima de 100%"
echo "  -- vizinho legitimo: a mesma cor escrita dentro da faixa e calculada, e reprova"
printf ':root { --fg: rgb(255, 255, 255); --bg: #777777; }\n.dark { --fg: #ffffff; --bg: #777777; }\n' > "$TMP/dentro.css"
python3 -m uiguards.contrast --config "$(cfg_para "$TMP/dentro.css")" \
  --pares "$TMP/pares-fg-bg.toml" > "$OUT" 2>&1; rc=$?; grep -E ":1 |TOTAL" "$OUT"
exigir_exit 1 "$rc" "rgb(255,255,255) sobre #777777 reprova"
exigir_texto "4.48:1 .*REPROVA" "a razao e a que a tela mostra"

echo
echo "===== (o) PAR COM TIPO ERRADO NA TABELA -> 2 ====="
echo "      (informativo = \"false\", texto, virava verdadeiro e tirava o par do gate)"
cat > "$TMP/pares-tipo.toml" <<'TOML'
[[par]]
frente = "--fg"
fundo = "--bg"
minimo = "texto"
rotulo = "par plantado fg sobre bg"
informativo = "false"
TOML
python3 -m uiguards.contrast --config "$(cfg_para "$TMP/sem-ponto-virgula.css")" \
  --pares "$TMP/pares-tipo.toml" > "$OUT" 2>&1; rc=$?; cat "$OUT"
exigir_exit 2 "$rc" "informativo como texto"
exigir_texto "tipo errado na configuracao \[par #1\] informativo" "a recusa nomeia o par e a chave"
echo "  -- o mesmo par com o booleano certo reprova (o par e ilegivel de fato)"
python3 -m uiguards.contrast --config "$(cfg_para "$TMP/sem-ponto-virgula.css")" \
  --pares "$TMP/pares-fg-bg.toml" > "$OUT" 2>&1; rc=$?; grep -E "TOTAL" "$OUT"
exigir_exit 1 "$rc" "informativo = false (booleano) reprova"


echo
echo "===== (N3) MINIMO DE INTERFACE E O DA NORMA, 3:1, NOS DOIS SENTIDOS ====="
cat > "$TMP/pares-interface.toml" <<'EOF'
[[par]]
frente = "--borda"
fundo = "--fundo"
minimo = "interface"
rotulo = "borda de campo perto do minimo"
informativo = false
EOF
for par in "9a9a9a 1" "8a8a8a 0"; do
  cor="${par% *}"; esperado="${par#* }"
  printf ':root { --borda: #%s; --fundo: #ffffff; }\n.dark { --borda: #%s; --fundo: #ffffff; }\n' "$cor" "$cor" > "$TMP/interface.css"
  python3 -m uiguards.contrast --config "$(cfg_para "$TMP/interface.css")" \
    --pares "$TMP/pares-interface.toml" > "$OUT" 2>&1; rc=$?; grep -E "borda de campo" "$OUT" | head -1
  exigir_exit "$esperado" "$rc" "borda #$cor sobre branco, categoria interface"
done

echo
echo "======================================================================"
if [ "$FALHAS" -eq 0 ]; then
  echo "PROVA DO GUARD 3: as $VERIFICACOES verificacoes fecharam."
  exit 0
fi
echo "PROVA DO GUARD 3: $FALHAS de $VERIFICACOES verificacoes NAO fecharam."
exit 1
