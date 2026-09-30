#!/usr/bin/env bash
# PROVA DO GUARD 5 -- as tres condicoes em que a varredura FALHA, a barreira
# do detector nao provado e a recusa de credencial invalida. Ela NAO falha por
# encontrar defeitos.
#
# Cada passo afirma o que espera; o script devolve 1 se alguma verificacao nao
# fechar. Tudo que a prova escreve vive num diretorio temporario proprio --
# caminho fixo em /tmp colide com outra execucao e com outra pessoa na mesma
# maquina.
set -u
cd "$(dirname "$0")/.."
export FIXTURE_USUARIO=operador FIXTURE_SENHA=senha-de-fixture
V="python3 sweep/executar.py"
TMP="$(mktemp -d)"
SONDA="uiguards/overflow_probe.js"
cp "$SONDA" "$TMP/sonda.bak"
# A sabotagem da etapa (d) e desfeita por trap, inclusive sob Ctrl+C ou tempo
# limite: restaurar so no fim deixaria o INSTRUMENTO sabotado no diretorio de
# trabalho, sem aviso.
restaurar() {
  [ -d "$TMP" ] || return 0
  cp "$TMP/sonda.bak" "$SONDA"
  rm -rf "$TMP"
}
trap 'exit 130' INT TERM
trap restaurar EXIT

FALHAS=0
VERIFICACOES=0
exigir_exit() {
  VERIFICACOES=$((VERIFICACOES + 1))
  if [ "$2" = "$1" ]; then echo "  [ok] $3: EXIT=$2"
  else echo "  [** FALHOU **] $3: EXIT=$2, esperava $1"; FALHAS=$((FALHAS + 1)); fi
}
exigir_texto() {
  VERIFICACOES=$((VERIFICACOES + 1))
  if grep -q "$2" "$1"; then echo "  [ok] $3"
  else echo "  [** FALHOU **] $3: nao achei '$2' na saida"; FALHAS=$((FALHAS + 1)); fi
}
exigir_igual() {
  VERIFICACOES=$((VERIFICACOES + 1))
  if [ "$2" = "$1" ]; then echo "  [ok] $3: $2"
  else echo "  [** FALHOU **] $3: $2, esperava $1"; FALHAS=$((FALHAS + 1)); fi
}
OUT="$TMP/saida.txt"

echo "===== (a) DESTINO DIVERGENTE -> o teste falha e a rota nao e gravada ====="
echo "      rota protegida declarada em area SEM sessao: redireciona para /login"
python3 - "$TMP" <<'PY'
import sys, pathlib
t = pathlib.Path("rotas.toml").read_text()
t = t.replace('rotas = ["/login", "/publico/precos"]',
              'rotas = ["/login", "/publico/precos", "/relatorios"]')
pathlib.Path(sys.argv[1], "rotas-destino.toml").write_text(t)
PY
$V --id prova-destino --saida "$TMP/saida-destino" --rotas "$TMP/rotas-destino.toml" > "$OUT" 2>&1
rc=$?
grep -E "DESTINO DIVERGENTE|FAILED|Ran |VARREDURA REPROVADA" "$OUT" | head -4
exigir_exit 1 "$rc" "destino divergente reprova a varredura"
exigir_texto "$OUT" "DESTINO DIVERGENTE" "a saida nomeia a divergencia"

echo
echo "===== (b) COBERTURA DE DETALHE ENCOLHIDA -> falha do teste ====="
echo "      identificadores resolvidos no viewport 'celular', onde a lista"
echo "      renderiza menos linhas: e por causa dela que as fichas saem de um"
echo "      viewport FIXO"
sed 's|viewport_de_resolucao = "desktop"|viewport_de_resolucao = "celular"|' rotas.toml \
  > "$TMP/rotas-cobertura.toml"
$V --id prova-cobertura --saida "$TMP/saida-cobertura" --rotas "$TMP/rotas-cobertura.toml" > "$OUT" 2>&1
rc=$?
grep -E "cobertura de paginas|Ran |FAILED" "$OUT" | head -3
exigir_exit 1 "$rc" "cobertura encolhida reprova a varredura"
exigir_texto "$OUT" "cobertura de paginas de detalhe encolheu" "a saida nomeia a cobertura"

echo
echo "===== (c) ESTADO INICIAL NAO APLICADO -> abortar alto ====="
python3 - <<'PY' > "$OUT" 2>&1
import sys, pathlib
sys.path.insert(0, str(pathlib.Path.cwd()))
from playwright.sync_api import sync_playwright
from sweep.varredura import conferir_estado_inicial, BASE_URL
with sync_playwright() as pw:
    nav = pw.chromium.launch()
    # contexto configurado ERRADO de proposito: escuro e sem movimento reduzido
    ctx = nav.new_context(viewport={"width":390,"height":844}, color_scheme="dark")
    pg = ctx.new_page(); pg.goto(f"{BASE_URL}/publico/precos")
    try:
        conferir_estado_inicial(pg)
        print("FALHOU A PROVA: aceitou o estado errado em silencio")
    except AssertionError as e:
        print(e)
    nav.close()
PY
cat "$OUT"
exigir_texto "$OUT" "ABORTANDO ALTO" "estado inicial errado aborta alto"

echo
echo "===== (d) DETECTOR NAO PROVADO BARRA A VARREDURA -> 2, e nenhum parcial ====="
# sabota a sonda: passa a devolver placar vazio sempre
sed -i 's|const achados = \[\];|const achados = []; if (true) { /* SABOTAGEM */ }|' "$SONDA"
sed -i 's|for (const el of document.querySelectorAll("\*")) {|for (const el of []) {|' "$SONDA"
$V --id prova-sabotada --saida "$TMP/saida-sabotada" > "$OUT" 2>&1
rc=$?
grep -E "FAILED|Ran |PROVA DO DETECTOR REPROVADA|NAO CONSIGO" "$OUT" | head -4
exigir_exit 2 "$rc" "detector reprovado e 'nao consigo executar'"
exigir_igual 0 "$(ls "$TMP/saida-sabotada" 2>/dev/null | wc -l)" "parciais gravados apos a reprovacao"
cp "$TMP/sonda.bak" "$SONDA"

echo
echo "===== (e) CREDENCIAL AUSENTE E CREDENCIAL RECUSADA -> 2 nos dois casos ====="
echo "      recusada nao e violacao: nenhuma rota foi medida, e 1 faria um"
echo "      problema de infraestrutura passar por divida de layout"
env -u FIXTURE_USUARIO -u FIXTURE_SENHA $V --id prova-sem-cred \
  --saida "$TMP/saida-sem-cred" > "$OUT" 2>&1
rc=$?; grep -E "NAO CONSIGO EXECUTAR" "$OUT" | head -1
exigir_exit 2 "$rc" "credencial ausente"
FIXTURE_SENHA=senha-errada $V --id prova-cred-errada \
  --saida "$TMP/saida-cred-errada" > "$OUT" 2>&1
rc=$?; grep -E "nao consegui autenticar|ERRO DE EXECUCAO" "$OUT" | head -2
exigir_exit 2 "$rc" "credencial recusada"
exigir_igual 0 "$(ls "$TMP/saida-cred-errada" 2>/dev/null | grep -c parcial)" "parciais apos credencial recusada"

echo
echo "===== (f) SUITE INTEIRA SOBRE A BASE SA -> 0 ====="
$V --id prova-sa --saida "$TMP/saida-sa" > "$OUT" 2>&1
rc=$?; tail -7 "$OUT"
exigir_exit 0 "$rc" "suite completa sobre a base sa"
exigir_igual 4 "$(ls "$TMP/saida-sa" | grep -c parcial)" "parciais gravados"
echo "capturas gravadas (apenas rotas com achado):"
ls "$TMP/saida-sa/capturas" | head -5
echo "  ... total: $(ls "$TMP/saida-sa/capturas" | wc -l) capturas para \
$(python3 -c "import json,glob,sys;print(sum(len(json.load(open(f))['registros']) for f in glob.glob(sys.argv[1]+'/parcial-*.json')))" "$TMP/saida-sa") registros"

echo
echo "===== (g) MATRIZ VAZIA OU COM TIPO ERRADO -> 2, e nenhum parcial ====="
echo "      medir nada nao e base limpa: sairia uma assinatura vazia e fixavel"
python3 - "$TMP" <<'PY'
import re, sys, pathlib
t = pathlib.Path("rotas.toml").read_text()
cab, resto = t.split("# --- viewports", 1)
vps, resto = resto.split("# --- areas", 1)
areas, fora = resto.split("# --- rotas excluidas", 1)
d = pathlib.Path(sys.argv[1])
# chave de topo em TOML vem antes do primeiro cabecalho de tabela
(d / "rotas-sem-viewport.toml").write_text("viewport = []\n" + cab + "# --- areas" + areas + "# --- rotas excluidas" + fora)
(d / "rotas-sem-area.toml").write_text("area = []\n" + cab + "# --- viewports" + vps + "# --- rotas excluidas" + fora)
(d / "rotas-area-vazia.toml").write_text(t.replace('rotas = ["/login", "/publico/precos"]', 'rotas = []'))
(d / "rotas-tipo.toml").write_text(t.replace("com_sessao = false", 'com_sessao = "false"', 1))
PY
for caso in sem-viewport sem-area area-vazia tipo; do
  $V --id "prova-$caso" --saida "$TMP/saida-$caso" --rotas "$TMP/rotas-$caso.toml" > "$OUT" 2>&1
  rc=$?; grep -E "NAO CONSIGO EXECUTAR" "$OUT" | head -1
  exigir_exit 2 "$rc" "matriz $caso"
  case "$caso" in tipo) motivo="tipo errado" ;; *) motivo="escopo vazio nao e base limpa" ;; esac
  exigir_texto "$OUT" "$motivo" "a recusa da matriz $caso diz o motivo"
  exigir_igual 0 "$(ls "$TMP/saida-$caso" 2>/dev/null | grep -c parcial)" "parciais gravados com a matriz $caso"
done

echo
echo "======================================================================"
if [ "$FALHAS" -eq 0 ]; then
  echo "PROVA DO GUARD 5: as $VERIFICACOES verificacoes fecharam."
  exit 0
fi
echo "PROVA DO GUARD 5: $FALHAS de $VERIFICACOES verificacoes NAO fecharam."
exit 1
