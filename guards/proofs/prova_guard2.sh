#!/usr/bin/env bash
# PROVA DO GUARD 2 -- as quatro regras, o escape hatch, a catraca PARA BAIXO
# E PARA CIMA, os dois modos, a recusa por baseline ausente, e a regra 4 lida
# na tag do truncamento: atributo em outra linha da mesma tag isenta, e
# atributo de um elemento vizinho nao isenta.
#
# CADA PASSO AFIRMA O QUE ESPERA. Um passo que imprime o codigo de saida e
# segue adiante nao prova nada: o passo (h) chegou a imprimir EXIT=0 sob o
# titulo "tem de REPROVAR" -- ele dependia de um arquivo em /tmp que so
# existia na maquina de quem escreveu a prova, e ninguem foi avisado. Agora o
# script devolve 1 quando qualquer verificacao nao fecha.
set -u
cd "$(dirname "$0")/.."
G="python3 -m uiguards.ratchet --config guards.toml"
LEGADO="fixtures/ui-src/components/RelatorioLegado.tsx"
PLANT="fixtures/ui-src/components/__PLANTIO2__.tsx"
PLANT_DUPLO="fixtures/ui-src/components/__PLANTIO::DUPLO__.tsx"
BASELINE="baseline-responsivo.json"
# Tudo que a prova toca no projeto volta ao estado de antes, inclusive se
# ela for interrompida: uma versao anterior deste script APAGAVA a baseline
# do projeto no final e nao a restaurava.
TMP="$(mktemp -d)"
cp "$LEGADO" "$TMP/legado.bak"
[ -f "$BASELINE" ] && cp "$BASELINE" "$TMP/baseline.bak"
restaurar() {
  [ -d "$TMP" ] || return 0            # idempotente: so restaura uma vez
  cp "$TMP/legado.bak" "$LEGADO"
  rm -f "$PLANT" "$PLANT_DUPLO"
  if [ -f "$TMP/baseline.bak" ]; then cp "$TMP/baseline.bak" "$BASELINE"; else rm -f "$BASELINE"; fi
  rm -rf "$TMP"
}
# Sinal so encerra; quem restaura e o trap de EXIT, que roda uma unica vez.
# Restaurar no proprio trap de sinal rodaria duas vezes -- e a segunda, sem
# o backup, apagaria a baseline do projeto.
trap 'exit 130' INT TERM
trap restaurar EXIT

FALHAS=0
VERIFICACOES=0
exigir_exit() {   # exigir_exit <esperado> <obtido> <rotulo>
  VERIFICACOES=$((VERIFICACOES + 1))
  if [ "$2" = "$1" ]; then
    echo "  [ok] $3: EXIT=$2"
  else
    echo "  [** FALHOU **] $3: EXIT=$2, esperava $1"
    FALHAS=$((FALHAS + 1))
  fi
}
exigir_texto() {  # exigir_texto <arquivo de saida> <padrao> <rotulo>
  VERIFICACOES=$((VERIFICACOES + 1))
  if grep -q "$2" "$1"; then
    echo "  [ok] $3"
  else
    echo "  [** FALHOU **] $3: nao achei '$2' na saida"
    FALHAS=$((FALHAS + 1))
  fi
}
exigir_ausente() { # exigir_ausente <arquivo de saida> <padrao> <rotulo>
  VERIFICACOES=$((VERIFICACOES + 1))
  if grep -q "$2" "$1"; then
    echo "  [** FALHOU **] $3: '$2' aparece na saida e nao podia"
    FALHAS=$((FALHAS + 1))
  else
    echo "  [ok] $3"
  fi
}
OUT="$TMP/saida.txt"

echo "===== (a) BASELINE AUSENTE -> tem de ser 2, nao 1 ====="
rm -f "$BASELINE"
$G --modo catraca; exigir_exit 2 "$?" "baseline ausente e 'nao consigo executar'"

echo
echo "===== (b) FIXAR A BASELINE DA DIVIDA LEGADA CONHECIDA ====="
$G --modo refixar; exigir_exit 0 "$?" "re-fixacao explicita"
echo "--- conteudo da baseline ---"; cat baseline-responsivo.json

echo
echo "===== (c) CATRACA SOBRE A BASE INALTERADA -> 0 ====="
$G --modo catraca > "$OUT"; rc=$?; tail -3 "$OUT"
exigir_exit 0 "$rc" "base inalterada passa"

echo
echo "===== (d) PLANTAR UMA VIOLACAO DE CADA UMA DAS QUATRO REGRAS ====="
cat > "$PLANT" <<'TSX'
import React from "react";
export function Plantio2({ rows }: any) {
  return (
    <div className="p-2">
      <table className="text-sm">
        <tbody>
          <tr>
            <td className="whitespace-nowrap px-2">{rows[0].descricao}</td>
          </tr>
        </tbody>
      </table>
      <div className="w-[480px]">largura fixa</div>
      <span className="truncate">{rows[0].endereco}</span>
    </div>
  );
}
TSX
$G --modo catraca > "$OUT"; rc=$?; cat "$OUT"
exigir_exit 1 "$rc" "divida nova reprova"
for regra in R1-tabela-sem-rolagem R2-largura-fixa-px R3-nowrap-conteudo-variavel R4-truncamento-sem-valor; do
  exigir_texto "$OUT" "$regra" "a saida nomeia $regra"
done

echo
echo "===== (e) A MESMA VIOLACAO COM ESCAPE HATCH E MOTIVO -> nao acusa ====="
cat > "$PLANT" <<'TSX'
import React from "react";
export function Plantio2() {
  return (
    <div className="p-2">
      {/* ui-guard-allow(responsivo): largura do slot de anuncio fixada por contrato com o veiculo */}
      <div className="w-[480px]">largura fixa</div>
    </div>
  );
}
TSX
$G --modo catraca > "$OUT"; rc=$?; tail -3 "$OUT"
exigir_exit 0 "$rc" "excecao declarada com motivo nao acusa"
rm -f "$PLANT"

echo
echo "===== (f) CATRACA PARA BAIXO: A DIVIDA CAIU -> tem de REPROVAR pedindo re-fixacao ====="
sed -i 's|w-\[720px\] ||' "$LEGADO"
$G --modo catraca > "$OUT"; rc=$?; cat "$OUT"
exigir_exit 1 "$rc" "divida reduzida sem re-fixacao reprova"
exigir_texto "$OUT" "RE-FIXE NO MESMO COMMIT" "a saida instrui a re-fixar"

echo
echo "===== (g) RE-FIXAR A BASELINE NO MESMO COMMIT ====="
$G --modo refixar; exigir_exit 0 "$?" "re-fixacao apos pagar divida"
grep -c 'R2-largura-fixa-px' baseline-responsivo.json | sed 's/^/chaves R2 na baseline agora: /'

echo
echo "===== (h) CATRACA PARA CIMA: A DIVIDA VOLTA AO VALOR DE ANTES -> tem de REPROVAR ====="
echo "      (e a re-fixacao exigida em (f) que torna este aumento visivel: sem ela, a"
echo "       baseline antiga ainda cobriria a violacao devolvida)"
# O backup vive no diretorio temporario desta execucao. A versao anterior
# lia /tmp/legado.bak -- caminho fixo, deixado por uma versao ainda mais
# antiga da prova -- e em maquina limpa este passo passava verde sem ter
# restaurado nada, exatamente sob o titulo que promete reprovacao.
cp "$TMP/legado.bak" "$LEGADO"
$G --modo catraca > "$OUT"; rc=$?; cat "$OUT"
exigir_exit 1 "$rc" "subir de novo depois da re-fixacao reprova"
exigir_texto "$OUT" "A DIVIDA CRESCEU" "a saida nomeia a chave que cresceu"

echo
echo "===== (i) MODO ESTRITO SOBRE BASE COM DIVIDA -> 1 ====="
$G --modo estrito > "$OUT"; rc=$?; tail -2 "$OUT"
exigir_exit 1 "$rc" "estrito reprova base com divida"

echo
echo "===== (j) MODO ESTRITO SOBRE BASE LIMPA -> 0 ====="
mv "$LEGADO" "$TMP/legado.hold"
$G --modo estrito > "$OUT"; rc=$?; tail -2 "$OUT"
mv "$TMP/legado.hold" "$LEGADO"
exigir_exit 0 "$rc" "estrito passa base limpa"

echo
echo "===== (k) REGRA 4 LE A TAG DO TRUNCAMENTO, NAO AS LINHAS AO REDOR ====="
echo "      linha 6:  title= na MESMA tag, cinco linhas abaixo    -> nao acusa"
echo "      linha 17: truncate com title= na propria tag          -> nao acusa"
echo "      linha 18: vizinho truncado SEM atributo               -> ACUSA"
echo "      linha 22: line-clamp-2 sem atributo                   -> ACUSA"
echo "      linha 26: line-clamp-3 com aria-label= na propria tag -> nao acusa"
# (g) re-fixou a baseline sem a R2 do legado, e (h) a devolveu. Re-fixar
# aqui, sobre o legado intacto, deixa o plantio como UNICA fonte de divida
# nova neste passo.
$G --modo refixar > /dev/null; exigir_exit 0 "$?" "baseline re-fixada sobre o legado intacto"
cat > "$PLANT" <<'TSX'
import React from "react";
export function Plantio2({ a, b, c }: any) {
  return (
    <div className="p-2">
      <span
        className="truncate"
        data-coluna="endereco"
        data-origem="cadastro"
        data-ordem="2"
        role="note"
        title={c}
      >
        {c}
      </span>
      <p className="text-sm">separador</p>
      <p className="text-sm">separador</p>
      <span className="truncate" title={a}>{a}</span>
      <span className="truncate">{b}</span>
      <p className="text-sm">separador</p>
      <p className="text-sm">separador</p>
      <p className="text-sm">separador</p>
      <p className="line-clamp-2">{b}</p>
      <p className="text-sm">separador</p>
      <p className="text-sm">separador</p>
      <p className="text-sm">separador</p>
      <p className="line-clamp-3" aria-label={a}>{a}</p>
    </div>
  );
}
TSX
$G --modo catraca > "$OUT"; rc=$?; cat "$OUT"
P="fixtures/ui-src/components/__PLANTIO2__.tsx"
exigir_exit 1 "$rc" "truncamentos sem valor exposto reprovam"
exigir_texto "$OUT" "__PLANTIO2__.tsx::R4-truncamento-sem-valor: conhecida 0 -> atual 2" \
  "exatamente dois truncamentos acusados no plantio"
exigir_texto "$OUT" "$P:18: " "o vizinho sem atributo e acusado, apesar do title= da linha de cima"
exigir_texto "$OUT" "$P:22: " "line-clamp sem atributo e acusado"
exigir_ausente "$OUT" "$P:6: " "title= em outra linha da mesma tag isenta, mesmo alem de tres linhas"
exigir_ausente "$OUT" "$P:17: " "title= na propria tag isenta"
exigir_ausente "$OUT" "$P:26: " "aria-label= na propria tag isenta o line-clamp"
rm -f "$PLANT"

echo
echo "===== (l) GRANULARIDADE: MOVER VIOLACOES DENTRO DO ARQUIVO -> 0 ====="
echo "      tres linhas novas no topo do legado e o truncamento levado para antes da"
echo "      largura fixa: as quatro violacoes mudam de linha, a contagem nao muda"
# A baseline vem de (k): o legado intacto.
python3 - "$LEGADO" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1]); linhas = p.read_text().split("\n")
trunc = next(i for i, l in enumerate(linhas) if 'className="truncate' in l)
movida = linhas.pop(trunc)
div = next(i for i, l in enumerate(linhas) if 'className="p-4"' in l)
linhas.insert(div + 1, movida)
linhas[1:1] = ["// linha acrescentada 1", "// linha acrescentada 2", "// linha acrescentada 3"]
p.write_text("\n".join(linhas))
PY
$G --modo estrito > "$OUT"; grep -E "RelatorioLegado.tsx:[0-9]+:" "$OUT"
exigir_texto "$OUT" "RelatorioLegado.tsx:12: w-\[720px\]" "a largura fixa mudou de linha (8 -> 12)"
exigir_texto "$OUT" "RelatorioLegado.tsx:11: <p className=\"truncate" "o truncamento mudou de linha e de ordem (26 -> 11)"
$G --modo catraca > "$OUT"; rc=$?; tail -1 "$OUT"
exigir_exit 0 "$rc" "violacoes so deslocadas nao sao divida nova"
cp "$TMP/legado.bak" "$LEGADO"

echo
echo "===== (m) GRANULARIDADE: UM ARQUIVO PERDE UMA R2 E OUTRO GANHA UMA -> 1 ====="
echo "      o total fica igual; a chave do arquivo que ganhou cresce, e reprova"
sed -i 's|w-\[720px\] ||' "$LEGADO"
cat > "$PLANT" <<'TSX'
import React from "react";
export function Plantio2() {
  return <div className="w-[480px]">largura fixa nova</div>;
}
TSX
$G --modo catraca > "$OUT"; rc=$?; cat "$OUT"
exigir_exit 1 "$rc" "divida trocada de arquivo reprova"
exigir_texto "$OUT" "contagem conhecida: 4   contagem atual: 4" "o total nao mudou"
exigir_texto "$OUT" "__PLANTIO2__.tsx::R2-largura-fixa-px: conhecida 0 -> atual 1" \
  "a saida nomeia a chave do arquivo que ganhou"
exigir_texto "$OUT" "RelatorioLegado.tsx::R2-largura-fixa-px: conhecida 1 -> atual 0" \
  "e a do arquivo que perdeu, pedindo re-fixacao"
cp "$TMP/legado.bak" "$LEGADO"
rm -f "$PLANT"

echo
echo "===== (n) LINHA DE EXPORT COM 'from' NO TEXTO NAO SOME DA ANALISE ====="
cat > "$PLANT" <<'TSX'
import React from "react";
export const T = () => <table className="w-[900px]"><tbody><tr><td>dados from api</td></tr></tbody></table>;
TSX
$G --modo estrito > "$OUT"; rc=$?; grep -E "__PLANTIO2__|TOTAL" "$OUT"
exigir_exit 1 "$rc" "estrito reprova"
exigir_texto "$OUT" "$P:2: export const T = () => <table" "a tabela sem contencao da linha exportada e acusada (R1)"
exigir_texto "$OUT" "$P:2: w-\[900px\]" "a largura fixa da linha exportada e acusada (R2)"
exigir_texto "$OUT" "TOTAL: 6 violacoes" "as quatro do legado mais as duas da linha exportada"
rm -f "$PLANT"

echo
echo "===== (o) REGRA 4: ATRIBUTO VAZIO NAO EXPOE VALOR ====="
echo "      linha 4: title=\"\"   -> ACUSA    linha 5: title={\"\"} -> ACUSA"
echo "      linha 6: title={a}  -> nao acusa (controle)"
cat > "$PLANT" <<'TSX'
import React from "react";
export function Plantio2({ a }: any) {
  return (<div>
      <span className="truncate" title="">{a}</span>
      <span className="truncate" title={""}>{a}</span>
      <span className="truncate" title={a}>{a}</span>
  </div>);
}
TSX
$G --modo catraca > "$OUT"; rc=$?; grep -E "__PLANTIO2__" "$OUT"
exigir_exit 1 "$rc" "truncamento com atributo vazio reprova"
exigir_texto "$OUT" "__PLANTIO2__.tsx::R4-truncamento-sem-valor: conhecida 0 -> atual 2" \
  "exatamente os dois vazios acusados"
exigir_texto "$OUT" "$P:4: " "title=\"\" acusado"
exigir_texto "$OUT" "$P:5: " "title={\"\"} acusado"
exigir_ausente "$OUT" "$P:6: " "title={a} continua isentando"
rm -f "$PLANT"

echo
echo "===== (p) RE-FIXAR NOMEIA A DIVIDA QUE CRESCEU (e grava assim mesmo) ====="
cat > "$PLANT" <<'TSX'
import React from "react";
export function Plantio2() {
  return <div className="w-[480px]">largura fixa nova</div>;
}
TSX
$G --modo refixar > "$OUT"; rc=$?; cat "$OUT"
exigir_exit 0 "$rc" "re-fixar continua gravando e saindo 0"
exigir_texto "$OUT" "ACEITOU divida MAIOR" "a re-fixacao avisa que a divida cresceu"
exigir_texto "$OUT" "__PLANTIO2__.tsx::R2-largura-fixa-px: conhecida 0 -> gravada 1" "e nomeia a chave"
exigir_texto baseline-responsivo.json "__PLANTIO2__.tsx::R2-largura-fixa-px\": 1" \
  "a mensagem nao mudou o que foi gravado"
rm -f "$PLANT"
$G --modo refixar > "$OUT"; rc=$?; cat "$OUT"
exigir_exit 0 "$rc" "re-fixar depois de pagar a divida"
exigir_ausente "$OUT" "ACEITOU divida MAIOR" "divida que so caiu nao gera o aviso"


echo
echo "===== (N) ESTADO DE PARTIDA RESTAURADO PARA AS ETAPAS SEGUINTES ====="
cp "$TMP/legado.bak" "$LEGADO"; cp "$TMP/baseline.bak" "$BASELINE"; rm -f "$PLANT"
$G --modo catraca > "$OUT" 2>&1; exigir_exit 0 "$?" "base do projeto limpa na catraca"

echo
echo "===== (N1b) MARCADOR COM MOTIVO SIMBOLICO NAO ISENTA A CATRACA ====="
cat > "$PLANT" <<'TSX'
import React from "react";
export function SemMotivo2() {
  return (<div className="w-[480px]">largura fixa</div>); /* ui-guard-allow: ok */
}
TSX
$G --modo catraca > "$OUT" 2>&1; rc=$?; cat "$OUT"
exigir_exit 1 "$rc" "motivo simbolico nao isenta a regra 2"
exigir_texto "$OUT" "R2-largura-fixa-px" "a regra 2 e nomeada"
rm -f "$PLANT"

echo
echo "===== (N2) LIMITE MAXIMO E MINIMO EM PX NAO SAO LARGURA FIXA ====="
cat > "$PLANT" <<'TSX'
import React from "react";
export function Limites() {
  return (<div className="max-w-[480px] min-w-[320px]">limitado</div>);
}
TSX
$G --modo catraca > "$OUT" 2>&1; rc=$?; cat "$OUT"
exigir_exit 0 "$rc" "max-w e min-w em px nao contam"
exigir_ausente "$OUT" "R2-largura-fixa-px" "a regra 2 nao aparece"
rm -f "$PLANT"

echo
echo "===== (N-c3) BASELINE COM CONTAGEM OU CHAVE INVALIDA -> 2, nunca 1 nem 0 ====="
for caso in negativa booleana fracionaria-inteira fracionaria sem-separador arquivo-vazio regra-inexistente; do
  cp "$TMP/baseline.bak" "$BASELINE"
  python3 - "$caso" "$BASELINE" <<'PYB'
import json, sys
caso, caminho = sys.argv[1], sys.argv[2]
d = json.load(open(caminho))
k = next(iter(d["chaves"]))
arquivo = k.split("::")[0]
if caso == "negativa":
    d["chaves"][k] = -1
elif caso == "booleana":
    d["chaves"][k] = True
elif caso == "fracionaria-inteira":
    d["chaves"][k] = 1.0
elif caso == "fracionaria":
    d["chaves"][k] = 0.5
elif caso == "arquivo-vazio":
    d["chaves"]["::" + k.split("::")[1]] = 1
elif caso == "sem-separador":
    d["chaves"][arquivo + "-sem-regra"] = 1
else:
    d["chaves"][arquivo + "::R9-inexistente"] = 1
json.dump(d, open(caminho, "w"), indent=2)
PYB
  $G --modo catraca > "$OUT" 2>&1; rc=$?; tail -1 "$OUT"
  exigir_exit 2 "$rc" "baseline invalida ($caso)"
done
cp "$TMP/baseline.bak" "$BASELINE"

echo
echo "===== (N-c3b) ARQUIVO COM '::' NO NOME: RE-FIXAR E A CATRACA SEGUINTE ACEITA ====="
echo "      o ultimo '::' da chave separa a regra; o nome do arquivo pode conter '::'"
cp "$TMP/baseline.bak" "$BASELINE"
cat > "$PLANT_DUPLO" <<'TSX'
import React from "react";
export function Duplo() {
  return (<div className="w-[480px]">largura fixa</div>);
}
TSX
$G --modo refixar > "$OUT" 2>&1; exigir_exit 0 "$?" "re-fixar com o arquivo de nome com '::'"
$G --modo catraca > "$OUT" 2>&1; rc=$?; tail -1 "$OUT"
exigir_exit 0 "$rc" "a catraca aceita a baseline que o re-fixar acabou de gravar"
rm -f "$PLANT_DUPLO"; cp "$TMP/baseline.bak" "$BASELINE"

echo
echo "===== (P-9) IMPORT SEGUIDO DE COMENTARIO DE LINHA CONTINUA SENDO IMPORT ====="
echo "      (o especificador de subpath traria uma largura fixa se a linha fosse avaliada)"
cp "$TMP/baseline.bak" "$BASELINE"
cat > "$PLANT" <<'TSX'
import largura from "#w-[480px]"; // subpath do pacote
TSX
$G --modo catraca > "$OUT" 2>&1; rc=$?; tail -1 "$OUT"
exigir_exit 0 "$rc" "a linha de import com comentario de linha nao e avaliada"
rm -f "$PLANT"

echo
echo "======================================================================"
if [ "$FALHAS" -eq 0 ]; then
  echo "PROVA DO GUARD 2: as $VERIFICACOES verificacoes fecharam."
  exit 0
fi
echo "PROVA DO GUARD 2: $FALHAS de $VERIFICACOES verificacoes NAO fecharam."
exit 1
