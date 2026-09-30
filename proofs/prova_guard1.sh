#!/usr/bin/env bash
# PROVA DO GUARD 1 -- fabrica um caso de CADA especie que o guard detecta,
# mais os casos de borda e as portas que ja foram abertas no escape hatch, e
# confere a recusa.
#
# Cada verificacao afirma o que espera; o script devolve 1 se alguma nao
# fechar. Contar so "deu 1" nao prova nada: a prova exige a ESPECIE certa, na
# quantidade certa, e exige silencio sobre o que e legitimo.
set -u
cd "$(dirname "$0")/.."
PLANT="fixtures/ui-src/components/__PLANTIO__.tsx"
CFGT="__cfg_prova1__.toml"
TMP="$(mktemp -d)"
trap 'exit 130' INT TERM
trap 'rm -f "$PLANT" "$CFGT"; rm -rf "$TMP"' EXIT
OUT="$TMP/saida.txt"

FALHAS=0
VERIFICACOES=0
exigir_exit() {
  VERIFICACOES=$((VERIFICACOES + 1))
  if [ "$2" = "$1" ]; then echo "  [ok] $3: EXIT=$2"
  else echo "  [** FALHOU **] $3: EXIT=$2, esperava $1"; FALHAS=$((FALHAS + 1)); fi
}
exigir_quantas() {  # exigir_quantas <n> <padrao> <rotulo>
  VERIFICACOES=$((VERIFICACOES + 1))
  achou=$(grep -c -- "$2" "$OUT" || true)
  if [ "$achou" = "$1" ]; then echo "  [ok] $3: $achou"
  else echo "  [** FALHOU **] $3: $achou ocorrencia(s) de '$2', esperava $1"; FALHAS=$((FALHAS + 1)); fi
}

cat > "$PLANT" <<'TSX'
import React from "react";

// Arquivo de plantio: um exemplar de cada especie.
export function Plantio({ n }: any) {
  return (
    <div className="p-4">
      {/* 1 escala do framework */}
      <span className="text-red-500">escala</span>
      {/* 1b escala com segmento de lado: mesma cor, mesma divida */}
      <div className="border-b-slate-300">escala com lado</div>
      {/* 1c marcador de prioridade como SUFIXO (versao nova do framework) */}
      <div className="bg-red-500!">escala com sufixo</div>
      {/* 2 cor absoluta com modificador de opacidade */}
      <div className="bg-white/80">absoluta</div>
      {/* 3 hexadecimal literal */}
      <div style={{ color: "#3366ff" }}>hex</div>
      {/* 4 rgb literal */}
      <div className="bg-[rgb(12,34,56)]">rgb</div>
      {/* 5 hsl literal, em maiuscula: CSS nao distingue caixa */}
      <div className="text-[HSL(210,50%,40%)]">hsl</div>
      {/* 6 combinacao proibida: fundo com texto diferente do declarado para ele */}
      <div className="bg-primary text-muted-foreground">combinacao</div>
      {/* 7 classe malformada: opacidade duplicada */}
      <div className="bg-card/80/80">malformada</div>
      {/* 8 cor de marca como cor de texto */}
      <p className="text-brand">marca como texto</p>
      {/* 9 notacao funcional moderna literal: uma de cada nome */}
      <div className="bg-[oklch(0.7_0.15_250)]">oklch em valor arbitrario</div>
      <div style={{ color: "lab(52% 40 60)" }}>lab em propriedade de estilo</div>
      <div style={{ borderColor: "lch(52% 72 50)" }}>lch em propriedade de estilo</div>
      <div className="text-[hwb(12_50%_0%)]">hwb</div>
      <div className="fill-[color(display-p3_1_0.5_0)]">color() com espaco de cor</div>
      {/* 9b notacao moderna EMBUTIDA em valor composto: PRECISA acusar */}
      <div className="shadow-[0_1px_2px_oklab(0.5_0.1_0.1)]">oklab composto</div>

      {/* USO CORRETO -- referencia a variavel: NAO pode acusar */}
      <div className="bg-[rgb(var(--brand))] text-[hsl(var(--ring))]">ok</div>
      {/* USO CORRETO na notacao moderna, direto e relativo: NAO pode acusar */}
      <div className="text-[oklch(var(--anel-oklch))] bg-[oklch(from_var(--anel-oklch)_l_c_h)]">ok</div>

      {/* NOTACAO EMBUTIDA EM VALOR MAIOR -- valor arbitrario com as partes
          unidas por `_`: PRECISA acusar */}
      <div className="shadow-[0_1px_2px_rgb(0,0,0)]">composto</div>

      {/* ESCAPE HATCH FALSIFICADO -- o marcador dentro de uma string nao e
          comentario, e uma URL na mesma linha nao o torna um: PRECISA acusar */}
      <a href="https://x" title="// ui-guard-allow: isto nao e um comentario"
         className="text-orange-500">falso escape</a>

      {/* EXCECAO LEGITIMA -- escape hatch com motivo: NAO pode acusar */}
      {/* ui-guard-allow: cor exigida pelo widget de terceiro que nao le tokens */}
      <div className="text-emerald-600">isento</div>

      {/* EXCECAO LEGITIMA com apostrofo no texto da mesma linha: o apostrofo
          nao pode anular o comentario que vem depois */}
      <span className="text-emerald-700">don't panic</span>{/* ui-guard-allow: mesma cor do widget de terceiro */}

      {/* ELEMENTO SO-DE-ICONE -- excecao legitima da especie 8 */}
      <button aria-label="Curtir" className="h-8 w-8 grid place-items-center text-brand">
        <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 2l12 12" /></svg>
      </button>
      {/* VARIANTE DE PSEUDO-ELEMENTO QUE DESENHA TEXTO -- conta como texto (especie 8) */}
      <input className="placeholder:text-brand" placeholder="busque aqui" />
    </div>
  );
}
TSX

echo "===== COM TODAS AS ESPECIES PLANTADAS ====="
python3 -m uiguards.palette --config guards.toml > "$OUT" 2>&1; rc=$?
cat "$OUT"
echo
echo "--- verificacoes ---"
exigir_exit 1 "$rc" "violacao plantada reprova"
# quatro exemplares de escala: text-red-500, border-b-slate-300 (segmento de
# lado), bg-red-500! (sufixo de prioridade) e text-orange-500 (o que o escape
# hatch falsificado tentava isentar).
exigir_quantas 1 "\[escala-framework\] Cor de escala do framework -- 4 ocorrencia(s)" \
  "especie 1 (escala) nomeada com os quatro exemplares"
exigir_quantas 1 "\[cor-absoluta\]" "especie 2 (cor absoluta) nomeada"
exigir_quantas 1 "\[hex-literal\]" "especie 3 (hexadecimal) nomeada"
exigir_quantas 1 "\[rgb-literal\]" "especie 4 (rgb) nomeada"
exigir_quantas 1 "\[hsl-literal\]" "especie 5 (hsl, em maiuscula) nomeada"
exigir_quantas 1 "\[combinacao-proibida\]" "especie 6 (combinacao) nomeada"
exigir_quantas 1 "\[classe-malformada\]" "especie 7 (malformada) nomeada"
exigir_quantas 1 "\[marca-como-texto\]" "especie 8 (marca como texto) nomeada"
# seis exemplares da notacao moderna: oklch, lab, lch, hwb, color() e o
# oklab embutido em valor composto.
exigir_quantas 1 "\[cor-funcional-moderna\] .* -- 6 ocorrencia(s)" \
  "especie 9 (notacao moderna) nomeada com os seis exemplares"
exigir_quantas 1 "oklab(0.5_0.1_0.1)" "notacao moderna embutida em valor arbitrario composto"
exigir_quantas 1 "\"lab(52% 40 60)\"" "notacao moderna em propriedade de estilo"
exigir_quantas 0 "var(--anel-oklch)" "referencia a variavel dentro de oklch() passa"
exigir_quantas 1 "bg-red-500!" "o sufixo de prioridade nao esconde a cor"
exigir_quantas 1 "border-b-slate-300" "o segmento de lado nao esconde a cor"
exigir_quantas 1 "rgb(0,0,0)" "notacao embutida em valor arbitrario composto"
exigir_quantas 1 "text-orange-500" "escape hatch falsificado (marcador em string) nao isenta"
exigir_quantas 2 "text-brand" "marca como texto: o paragrafo e o pseudo-elemento"
exigir_quantas 0 "text-emerald-600" "escape hatch legitimo isenta"
exigir_quantas 0 "text-emerald-700" "apostrofo no texto nao anula o escape hatch da linha"
exigir_quantas 0 "var(--brand)" "referencia a variavel dentro de hsl() passa"
exigir_quantas 0 "aria-label=\"Curtir\"" "controle sem texto, so icone, fica fora da especie 8"

P="fixtures/ui-src/components/__PLANTIO__.tsx"

echo
echo "===== (A1) LINHA DE EXPORT COM 'from' NO TEXTO OU NO GRADIENTE NAO E IMPORTACAO ====="
echo "      linha 2: reexportacao de verdade (termina no especificador) -> nao avaliada"
echo "      linha 3: componente exportado numa linha, gradiente from-*   -> ACUSA as tres escalas"
echo "      linha 4: componente exportado com 'from' no texto            -> ACUSA escala e hex"
cat > "$PLANT" <<'TSX'
import React from "react";
export * from "./paleta#3366ff";
export const Faixa = () => <div className="bg-gradient-to-r from-red-500 to-blue-500 text-emerald-600">faixa</div>;
export const Aviso = () => <div className="bg-red-500 text-[#ff0000]">Dados from API</div>;
TSX
python3 -m uiguards.palette --config guards.toml > "$OUT" 2>&1; rc=$?; cat "$OUT"
exigir_exit 1 "$rc" "componente exportado numa linha so e avaliado"
exigir_quantas 1 "\[escala-framework\] Cor de escala do framework -- 4 ocorrencia(s)" \
  "as quatro escalas das linhas 3 e 4 (from-red-500, to-blue-500, text-emerald-600, bg-red-500)"
exigir_quantas 1 "$P:3: from-red-500" "o utilitario de gradiente from-* nao apaga a linha"
exigir_quantas 1 "$P:4: .*Dados from API" "a palavra 'from' no texto nao apaga a linha (hex acusado)"
exigir_quantas 0 "3366ff" "a reexportacao de verdade continua fora da analise"

echo
echo "===== (A6, B6) ESPECIE 6: MEDIDA NAO E COR, E CADA ALTERNATIVA E JULGADA SOZINHA ====="
echo "      linha 4: fundo com o token certo e text-[13px] (tamanho)        -> nao acusa"
echo "      linha 5: condicional, so uma alternativa com o fundo solido     -> nao acusa a outra"
echo "      linha 6: controle -- fundo com texto que nao e o token dele     -> ACUSA"
cat > "$PLANT" <<'TSX'
import React from "react";
export function Seis({ ok }: any) {
  return (<div>
      <button className="bg-primary text-primary-foreground text-[13px]">Salvar</button>
      <button className={ok ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}>Enviar</button>
      <div className="bg-card text-muted-foreground">combinacao proibida de controle</div>
  </div>);
}
TSX
python3 -m uiguards.palette --config guards.toml > "$OUT" 2>&1; rc=$?; cat "$OUT"
exigir_exit 1 "$rc" "o controle reprova"
exigir_quantas 1 "\[combinacao-proibida\] .* -- 1 ocorrencia(s)" "exatamente uma combinacao proibida"
exigir_quantas 1 "$P:6: bg-card ... text-muted-foreground" "a acusada e a do controle"
exigir_quantas 0 "text-\[13px\]" "tamanho de fonte arbitrario nao e cor de texto"
exigir_quantas 0 "$P:5: " "a alternativa sem o fundo solido nao e acusada"

echo
echo "===== (B2) ESPECIE 8 EM MARCACAO DE VARIAS LINHAS ====="
echo "      linhas 4-9:   <p> com a classe duas linhas abaixo da tag e texto literal -> ACUSA"
echo "      linhas 10-15: botao que so tem icone, com a tag em varias linhas     -> nao acusa"
cat > "$PLANT" <<'TSX'
import React from "react";
export function Multi() {
  return (<div>
      <p
        data-coluna="aviso"
        className="text-brand"
      >
        texto literal do aviso
      </p>
      <button
        aria-label="Fechar"
        className="text-brand"
      >
        <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 2l12 12" /></svg>
      </button>
  </div>);
}
TSX
python3 -m uiguards.palette --config guards.toml > "$OUT" 2>&1; rc=$?; cat "$OUT"
exigir_exit 1 "$rc" "marcacao multilinha com texto reprova"
exigir_quantas 1 "\[marca-como-texto\] .* -- 1 ocorrencia(s)" "uma so acusacao da especie 8"
exigir_quantas 1 "$P:6: text-brand" "a acusada e a classe do <p>, duas linhas abaixo da tag"
exigir_quantas 0 "$P:12: " "o botao que so tem icone, em varias linhas, nao e acusado"

echo
echo "===== (C3) MARCADOR AO LADO DE CODIGO ISENTA SO A PROPRIA LINHA ====="
echo "      linha 4: violacao + marcador no fim da mesma linha       -> nao acusa"
echo "      linha 5: violacao logo abaixo, sem marcador proprio      -> ACUSA"
echo "      linha 7: violacao abaixo de um marcador SOZINHO na linha -> nao acusa"
cat > "$PLANT" <<'TSX'
import React from "react";
export function Posicao() {
  return (<div>
      <div className="text-red-500">um</div>{/* ui-guard-allow: widget de terceiro exige esta cor */}
      <div className="text-blue-500">dois, sem marcador para esta linha</div>
      {/* ui-guard-allow: cor fixada pelo contrato do widget de terceiro */}
      <div className="text-lime-500">tres</div>
  </div>);
}
TSX
python3 -m uiguards.palette --config guards.toml > "$OUT" 2>&1; rc=$?; cat "$OUT"
exigir_exit 1 "$rc" "a linha sem motivo reprova"
exigir_quantas 1 "$P:5: text-blue-500" "o marcador da linha 4 nao alcanca a linha 5"
exigir_quantas 0 "text-red-500" "o marcador isenta a propria linha"
exigir_quantas 0 "text-lime-500" "o marcador sozinho na linha isenta a seguinte"

rm -f "$PLANT"

echo
echo "===== (A3) CONFIGURACAO COM TIPO ERRADO -> 2, nunca um valor reinterpretado ====="
# A configuracao alterada fica na raiz do kit, como a verdadeira: num outro
# diretorio a raiz de UI deixaria de existir e o 2 viria por esse motivo.
python3 - "$CFGT" <<'PY'
import pathlib, sys
t = pathlib.Path("guards.toml").read_text()
t = t.replace('familias = [', 'familias = "slate"\nfamilias_antigas = [', 1)
pathlib.Path(sys.argv[1]).write_text(t)
PY
python3 -m uiguards.palette --config "$CFGT" > "$OUT" 2>&1; rc=$?; tail -1 "$OUT"
exigir_exit 2 "$rc" "familias como texto, e nao lista"
exigir_quantas 1 "tipo errado na configuracao \[paleta\] familias" "a recusa nomeia a chave e o tipo"
sed 's|^variantes_rotulo = \["file", "placeholder"\]|variantes_rotulo = "file"|' guards.toml > "$CFGT"
python3 -m uiguards.palette --config "$CFGT" > "$OUT" 2>&1; rc=$?; tail -1 "$OUT"
exigir_exit 2 "$rc" "variantes_rotulo como texto, e nao lista"
exigir_quantas 1 "tipo errado na configuracao \[paleta\] variantes_rotulo" "a recusa nomeia a chave"
cp guards.toml "$CFGT"
python3 -m uiguards.palette --config "$CFGT" > "$OUT" 2>&1; rc=$?; tail -1 "$OUT"
exigir_exit 0 "$rc" "a mesma copia com os tipos certos passa (o 2 acima nao veio do lugar do arquivo)"
rm -f "$CFGT"

echo
echo "===== APOS REMOVER O PLANTIO ====="
python3 -m uiguards.palette --config guards.toml > "$OUT" 2>&1; rc=$?
tail -2 "$OUT"
exigir_exit 0 "$rc" "base limpa passa"


echo
echo "===== (N1) COR ARBITRARIA DE TEXTO AO LADO DE FUNDO SOLIDO -> combinacao proibida ====="
echo "      o outro lado do A6: valor arbitrario que nao e medida continua sendo cor"
cat > "$PLANT" <<'TSX'
import React from "react";
export function CorArbitraria() {
  return (<div className="bg-primary text-[var(--qualquer)]">cor arbitraria</div>);
}
TSX
python3 -m uiguards.palette --config guards.toml > "$OUT" 2>&1; rc=$?; cat "$OUT"
exigir_exit 1 "$rc" "cor arbitraria de texto ao lado de bg-primary reprova"
exigir_quantas 1 "^\[combinacao-proibida\]" "a especie combinacao-proibida e nomeada"
rm -f "$PLANT"

echo
echo "===== (N1b) MARCADOR SEM MOTIVO NAO ISENTA ====="
echo "      linha 4: marcador vazio         -> ACUSA"
echo "      linha 5: motivo de duas letras  -> ACUSA"
cat > "$PLANT" <<'TSX'
import React from "react";
export function SemMotivo() {
  return (<div>
      <div className="text-red-500">um</div>{/* ui-guard-allow: */}
      <div className="text-blue-500">dois</div>{/* ui-guard-allow: ok */}
  </div>);
}
TSX
python3 -m uiguards.palette --config guards.toml > "$OUT" 2>&1; rc=$?; cat "$OUT"
exigir_exit 1 "$rc" "marcador sem motivo nao isenta"
exigir_quantas 1 "$P:4: text-red-500" "marcador vazio nao isenta a linha 4"
exigir_quantas 1 "$P:5: text-blue-500" "motivo simbolico nao isenta a linha 5"
rm -f "$PLANT"

echo
echo "===== (N-c1) CODIGO ENTRE DOIS COMENTARIOS DE BLOCO NA LINHA DE UM IMPORT ====="
echo "      o fim da declaracao aceitava /* ... */ guloso, do primeiro ao ultimo"
cat > "$PLANT" <<'TSX'
import a from "a"; /* x */ export const C = "bg-red-500"; /* y */
TSX
python3 -m uiguards.palette --config guards.toml > "$OUT" 2>&1; rc=$?; cat "$OUT"
exigir_exit 1 "$rc" "o codigo entre os dois comentarios e avaliado"
exigir_quantas 1 "$P:1: bg-red-500" "a cor de escala entre os comentarios e acusada"
echo "      vizinho legitimo: import seguido so de comentarios continua sendo import"
echo "      (o especificador '#fff' de subpath seria hex se a linha fosse avaliada)"
cat > "$PLANT" <<'TSX'
import cores from "#fff"; /* a */ /* b */
TSX
python3 -m uiguards.palette --config guards.toml > "$OUT" 2>&1; rc=$?; tail -1 "$OUT"
exigir_exit 0 "$rc" "import seguido de dois comentarios de bloco nao e avaliado"
cat > "$PLANT" <<'TSX'
import cores from "#fff"; // paleta de subpath
TSX
python3 -m uiguards.palette --config guards.toml > "$OUT" 2>&1; rc=$?; tail -1 "$OUT"
exigir_exit 0 "$rc" "import seguido de comentario de linha nao e avaliado"
rm -f "$PLANT"

echo
echo "======================================================================"
if [ "$FALHAS" -eq 0 ]; then
  echo "PROVA DO GUARD 1: as $VERIFICACOES verificacoes fecharam."
  exit 0
fi
echo "PROVA DO GUARD 1: $FALHAS de $VERIFICACOES verificacoes NAO fecharam."
exit 1
