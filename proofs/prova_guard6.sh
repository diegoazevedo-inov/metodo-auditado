#!/usr/bin/env bash
# PROVA DO GUARD 6 -- reprodutibilidade da assinatura, as quatro recusas, o
# guard de ancora nos dois estados, e a conferencia do resumo criptografico
# com a ferramenta padrao do sistema.
#
# Cada passo afirma o que espera; o script devolve 1 se alguma verificacao nao
# fechar. Tudo vive num diretorio temporario proprio, o servidor auxiliar sobe
# numa porta livre escolhida na hora e e encerrado no trap -- caminho e porta
# fixos colidem com outra execucao, e a versao anterior deixava o servidor no
# ar depois de terminar.
set -u
cd "$(dirname "$0")/.."
export FIXTURE_USUARIO=operador FIXTURE_SENHA=senha-de-fixture
V="python3 sweep/executar.py"
C="python3 -m uiguards.consolidate"
TMP="$(mktemp -d)"
AUX_PID=""
limpar() {
  [ -n "$AUX_PID" ] && kill "$AUX_PID" 2>/dev/null
  rm -rf "$TMP"
}
trap 'exit 130' INT TERM
trap limpar EXIT

FALHAS=0
VERIFICACOES=0
exigir_exit() {
  VERIFICACOES=$((VERIFICACOES + 1))
  if [ "$2" = "$1" ]; then echo "  [ok] $3: EXIT=$2"
  else echo "  [** FALHOU **] $3: EXIT=$2, esperava $1"; FALHAS=$((FALHAS + 1)); fi
}
exigir_igual() {
  VERIFICACOES=$((VERIFICACOES + 1))
  if [ "$2" = "$1" ]; then echo "  [ok] $3: $2"
  else echo "  [** FALHOU **] $3: $2, esperava $1"; FALHAS=$((FALHAS + 1)); fi
}
exigir_texto() {
  VERIFICACOES=$((VERIFICACOES + 1))
  if grep -q "$2" "$1"; then echo "  [ok] $3"
  else echo "  [** FALHOU **] $3: nao achei '$2' na saida"; FALHAS=$((FALHAS + 1)); fi
}
OUT="$TMP/saida.txt"

echo "===== (a) DUAS EXECUCOES INDEPENDENTES -> ASSINATURA IDENTICA ====="
$V --id "execucao-um"   --saida "$TMP/exec1" >/dev/null 2>&1; exigir_exit 0 "$?" "varredura 1"
$V --id "execucao-dois" --saida "$TMP/exec2" >/dev/null 2>&1; exigir_exit 0 "$?" "varredura 2"
$C --parciais "$TMP/exec1" >/dev/null; exigir_exit 0 "$?" "consolidacao 1"
$C --parciais "$TMP/exec2" >/dev/null; exigir_exit 0 "$?" "consolidacao 2"
echo "  assinatura 1: $(sha256sum < "$TMP/exec1/assinatura.txt")"
echo "  assinatura 2: $(sha256sum < "$TMP/exec2/assinatura.txt")"
if diff -q "$TMP/exec1/assinatura.txt" "$TMP/exec2/assinatura.txt" >/dev/null; then
  VERIFICACOES=$((VERIFICACOES + 1))
  echo "  [ok] >>> ASSINATURAS IDENTICAS: a baseline pode ser dada por fixada."
  echo "  (identificadores de execucao diferentes -- 'execucao-um' e 'execucao-dois' --"
  echo "   e ainda assim as assinaturas batem: nelas nao entra data, hora nem excedente)"
else
  VERIFICACOES=$((VERIFICACOES + 1)); FALHAS=$((FALHAS + 1))
  echo "  [** FALHOU **] assinaturas divergentes"
  diff "$TMP/exec1/assinatura.txt" "$TMP/exec2/assinatura.txt" | head
fi
echo "  primeiras linhas da assinatura:"; head -3 "$TMP/exec1/assinatura.txt" | sed 's/^/    /'
# Spec, GUARD 6: o relatorio segue o contrato de determinismo, e duas medicoes
# de uma interface que nao mudou produzem arquivos iguais byte a byte, provados
# pelo resumo criptografico. O identificador da execucao vive so nos parciais.
cmp -s "$TMP/exec1/relatorio.txt" "$TMP/exec2/relatorio.txt" && r=identicos || r=diferentes
exigir_igual identicos "$r" "relatorio.txt igual byte a byte entre as duas execucoes"
cmp -s "$TMP/exec1/resumos.sha256" "$TMP/exec2/resumos.sha256" && r=identicos || r=diferentes
exigir_igual identicos "$r" "resumos.sha256 igual byte a byte entre as duas execucoes"
# A assinatura traz so defeitos de pagina: nenhum da moldura pode entrar nela.
python3 - "$TMP/exec1" > "$OUT" <<'PYM'
import glob, json, os, sys
d = sys.argv[1]
assinatura = set(open(os.path.join(d, "assinatura.txt"), encoding="utf-8").read().splitlines())
moldura = set()
for f in sorted(glob.glob(os.path.join(d, "parcial-*.json"))):
    p = json.load(open(f, encoding="utf-8"))
    vp = p["viewport"]["nome"]
    for r in p["registros"]:
        for a in r.get("achados", []):
            if a.get("no_placar") and not a.get("sob_ancora_conteudo"):
                moldura.add(f'{vp}\t{r["rota"]}\t{a["especie"]}\t{a["seletor"]}')
print("moldura", len(moldura))
print("na_assinatura", len(moldura & assinatura))
PYM
cat "$OUT"
exigir_igual 0 "$(awk '/^na_assinatura/{print $2}' "$OUT")" "nenhum defeito da moldura entra na assinatura"
[ "$(awk '/^moldura/{print $2}' "$OUT")" -gt 0 ] && r=sim || r=nao
exigir_igual sim "$r" "a fixture tem defeito de moldura, entao a verificacao acima nao e vazia"

echo
echo "===== (b) CONFERENCIA DO RESUMO COM A FERRAMENTA PADRAO DO SISTEMA ====="
( cd "$TMP/exec1" && sha256sum -c resumos.sha256 ); exigir_exit 0 "$?" "sha256sum -c"

echo
echo "===== (c) PARCIAL AUSENTE -> 2 ====="
cp -r "$TMP/exec1" "$TMP/exec3" && rm "$TMP/exec3/parcial-tablet.json"
$C --parciais "$TMP/exec3" > "$OUT" 2>&1; rc=$?; cat "$OUT"
exigir_exit 2 "$rc" "parcial ausente"

echo
echo "===== (d) IDENTIFICADORES DE EXECUCAO DIFERENTES -> 2 ====="
cp -r "$TMP/exec1" "$TMP/exec4"
python3 - "$TMP/exec4/parcial-tablet.json" <<'PY'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1])
d = json.loads(p.read_text()); d["identificador_execucao"] = "outra-execucao"
p.write_text(json.dumps(d, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
PY
$C --parciais "$TMP/exec4" > "$OUT" 2>&1; rc=$?; cat "$OUT"
exigir_exit 2 "$rc" "mistura de execucoes"

echo
echo "===== (e) SEM IDENTIFICADOR (variavel de ambiente esquecida) -> 2 ====="
$V --saida "$TMP/exec5" >/dev/null 2>&1
echo "  a varredura gravou com o sentinela: \
$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['identificador_execucao'])" "$TMP/exec5/parcial-tablet.json")"
$C --parciais "$TMP/exec5" > "$OUT" 2>&1; rc=$?; cat "$OUT"
exigir_exit 2 "$rc" "identificador ausente"

echo
echo "===== (f) ANCORA RENOMEADA NA APLICACAO, COM DEFEITOS PRESENTES -> recusa ====="
PORTA=$(python3 -c "import socket; s=socket.socket(); s.bind(('127.0.0.1',0)); print(s.getsockname()[1]); s.close()")
sed 's/data-ui-content/data-ui-conteudo-renomeado/' fixtures/site/servidor.py > "$TMP/servidor_renomeado.py"
python3 "$TMP/servidor_renomeado.py" "$PORTA" >/dev/null 2>&1 &
AUX_PID=$!
for _ in $(seq 1 50); do
  python3 -c "import socket,sys; s=socket.socket(); sys.exit(s.connect_ex(('127.0.0.1',$PORTA)))" && break
  sleep 0.1
done
echo "  aplicacao auxiliar (ancora renomeada) na porta $PORTA, pid $AUX_PID"
$V --id "exec-ancora" --saida "$TMP/exec6" --base-url "http://127.0.0.1:$PORTA" >/dev/null 2>&1
exigir_exit 0 "$?" "varredura contra a aplicacao com a ancora renomeada"
$C --parciais "$TMP/exec6" > "$OUT" 2>&1; rc=$?; cat "$OUT"
exigir_exit 2 "$rc" "marcacao obsoleta com defeitos presentes"
kill "$AUX_PID" 2>/dev/null; AUX_PID=""

echo
echo "===== (g) PLACAR ZERO -> guard de ancora NAO APLICADO, com AVISO, assinatura vazia ====="
python3 - "$TMP/rotas-limpo.toml" <<'PY'
import pathlib, sys
t = pathlib.Path("rotas.toml").read_text()
t = t.split("# --- viewports")[0] + '''
[[viewport]]
nome = "desktop"
largura = 1280
altura = 800

[[area]]
nome = "publica"
com_sessao = false
rotas = ["/publico/precos"]

[[fora_de_escopo]]
rota = "/sair"
motivo = "encerra a sessao"
'''
pathlib.Path(sys.argv[1]).write_text(t)
PY
$V --id "exec-limpa" --saida "$TMP/exec7" --rotas "$TMP/rotas-limpo.toml" >/dev/null 2>&1
exigir_exit 0 "$?" "varredura sobre superficie sem defeito"
$C --parciais "$TMP/exec7" --rotas "$TMP/rotas-limpo.toml" > "$OUT" 2>&1; rc=$?
grep -E "AVISO|defeitos de|assinatura|tupla" "$OUT"
exigir_exit 0 "$rc" "consolidacao no placar zero"
exigir_texto "$OUT" "AVISO" "a nao aplicacao do guard de ancora e avisada"
exigir_igual 0 "$(wc -c < "$TMP/exec7/assinatura.txt")" "bytes da assinatura vazia"
( cd "$TMP/exec7" && sha256sum -c resumos.sha256 >/dev/null 2>&1 ); exigir_exit 0 "$?" "resumo fecha no estado final"

echo
echo "===== (h) ROTA QUE RESPONDE ERRO HTTP NO PROPRIO ENDERECO -> nao medivel, QUEBRADA ====="
echo "      /clientes/c-9999 e /relatorioz respondem 404, /erro/500 e /erro/503 respondem"
echo "      erro de servidor, todas na propria URL. A pagina de"
echo "      erro renderiza e poderia ser medida, mas nao e a pagina da rota"
python3 - "$TMP/rotas-404.toml" <<'PY'
import pathlib, sys
t = pathlib.Path("rotas.toml").read_text()
t = t.replace('rotas = ["/", "/clientes", "/relatorios"]',
              'rotas = ["/", "/clientes", "/relatorios", "/clientes/c-9999", "/relatorioz",'
              ' "/erro/500", "/erro/503"]')
pathlib.Path(sys.argv[1]).write_text(t)
PY
$V --id "exec-404" --saida "$TMP/exec8" --rotas "$TMP/rotas-404.toml" >/dev/null 2>&1
exigir_exit 0 "$?" "a varredura nao falha: a rota chega ao proprio endereco"
$C --parciais "$TMP/exec8" --rotas "$TMP/rotas-404.toml" > "$OUT" 2>&1; rc=$?
grep -E "medicoes de rota|rotas quebradas|rotas saudaveis|NAO MEDIVEIS|HTTP" "$OUT" | head -8
exigir_exit 0 "$rc" "consolidacao com rotas nao mediveis"
exigir_texto "$OUT" "rotas NAO MEDIVEIS          : 16" "quatro rotas nao mediveis em cada um dos quatro viewports"
exigir_texto "$OUT" "HTTP 500" "o relatorio nomeia o 500"
exigir_texto "$OUT" "HTTP 503" "o relatorio nomeia o 503"
exigir_texto "$OUT" "rotas saudaveis             : 30" "nenhuma delas conta como rota em ordem (30, como sem elas)"
exigir_texto "$OUT" "\[desktop\] /relatorioz: a resposta principal do proprio endereco foi HTTP 404" \
  "o relatorio nomeia a rota e o status"
exigir_igual 0 "$(python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
print(sum(len(r['achados']) for r in d['registros'] if r.get('nao_medivel')))" "$TMP/exec8/parcial-celular.json")" \
  "achados gravados para a pagina de erro"

echo
echo "===== (i) MESMO IDENTIFICADOR, ROTAS MEDIDAS DIFERENTES -> 2 ====="
echo "      (um parcial de outra matriz, com o id repetido, se juntava sem recusa)"
cp -r "$TMP/exec1" "$TMP/exec9"
python3 - "$TMP/exec9/parcial-desktop.json" <<'PY'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1]); d = json.loads(p.read_text())
d["escopo_aplicado"]["rotas_medidas"].remove("/relatorios")
d["registros"] = [r for r in d["registros"] if r["rota"] != "/relatorios"]
p.write_text(json.dumps(d, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
PY
$C --parciais "$TMP/exec9" > "$OUT" 2>&1; rc=$?; head -3 "$OUT"
exigir_exit 2 "$rc" "escopo medido divergente com o mesmo identificador"
exigir_texto "$OUT" "rotas_medidas" "a recusa nomeia o campo que diverge"

echo
echo "===== (j) PARCIAIS SEM NENHUMA ROTA -> 2, nunca assinatura vazia fixavel ====="
cp -r "$TMP/exec7" "$TMP/exec10"
python3 - "$TMP/exec10/parcial-desktop.json" <<'PY'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1]); d = json.loads(p.read_text())
d["escopo_aplicado"]["rotas_medidas"] = []
d["registros"] = []
p.write_text(json.dumps(d, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
PY
$C --parciais "$TMP/exec10" --rotas "$TMP/rotas-limpo.toml" > "$OUT" 2>&1; rc=$?; cat "$OUT"
exigir_exit 2 "$rc" "execucao que mediu nenhuma rota"
exigir_texto "$OUT" "escopo vazio nao e base limpa" "a recusa diz o motivo"

echo
echo "======================================================================"
if [ "$FALHAS" -eq 0 ]; then
  echo "PROVA DO GUARD 6: as $VERIFICACOES verificacoes fecharam."
  exit 0
fi
echo "PROVA DO GUARD 6: $FALHAS de $VERIFICACOES verificacoes NAO fecharam."
exit 1
