"""
Base compartilhada dos seis verificadores.

Concentra o que o contrato comum da spec exige que seja idêntico nos seis:
o significado dos codigos de saida, o formato do escape hatch, a leitura de
configuracao e a varredura lexica que separa codigo de comentario.

CODIGOS DE SAIDA (contrato comum, identico nos seis):
    0 -> executei e esta limpo
    1 -> executei e ACHEI violacao
    2 -> NAO CONSIGO EXECUTAR (entrada ausente, malformada, config invalida)

Confundir 2 com 1 e o pior modo de falha: um verificador quebrado passaria
por base limpa. Por isso toda falha de execucao desta base levanta
`GuardCannotRun`, que os pontos de entrada traduzem para 2 -- nunca para 1.
"""

from __future__ import annotations

import os
import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

EXIT_CLEAN = 0
EXIT_VIOLATION = 1
EXIT_CANNOT_RUN = 2


class GuardCannotRun(Exception):
    """Entrada ausente, malformada ou configuracao invalida. Traduz para 2."""


# --------------------------------------------------------------------------
# Escape hatch
# --------------------------------------------------------------------------
# Formato unico nos seis guards: um marcador em comentario acompanhado de
# motivo escrito. Posicao aceita: a propria linha isentada, ou a linha logo
# acima dela DESDE QUE o comentario seja tudo o que ha nessa linha. Marcador
# que divide a linha com codigo isenta so aquela linha: valendo tambem para a
# seguinte, ele isentava uma segunda violacao que nao tinha motivo nenhum.
# Marcador sem motivo NAO e aceito pelo formato: sem justificativa escrita,
# quem revisa nao tem o que avaliar.

ESCAPE_MARKER = "ui-guard-allow"
MIN_REASON_CHARS = 10

_ESCAPE_RE = re.compile(
    re.escape(ESCAPE_MARKER) + r"(?:\(([a-z0-9_,\-]*)\))?\s*:\s*(.*)$"
)


@dataclass(frozen=True)
class Escape:
    scope: str | None   # None = vale para todos os guards
    reason: str
    line: int


def _abre_comentario_fora_de_string(linha: str, ate: int) -> bool:
    """
    Existe abridor de comentario antes de `ate`, FORA de literal de string?

    Procurar o abridor por substring simples aceitava marcador escrito dentro
    de uma string -- `title="// ui-guard-allow: ..."` -- como se fosse
    comentario, e ate um `href="https://..."` na mesma linha bastava para
    fornecer o `//`. Excecao tem de se declarar em comentario, entao o
    abridor precisa estar em codigo, nao dentro de aspas.
    """
    i, n = 0, min(ate, len(linha))
    while i < n:
        ch = linha[i]
        if ch in "\"'`":
            i += 1
            while i < n and linha[i] != ch:
                i += 2 if linha[i] == "\\" else 1
            i += 1
            continue
        if linha.startswith(("//", "/*", "<!--"), i):
            return True
        i += 1
    return False


def parse_escape(line_text: str, line_no: int,
                 em_comentario: bool | None = None) -> Escape | None:
    """
    Le um escape hatch de uma linha. Exige comentario E motivo escrito.

    `em_comentario` vem de quem ja lexou o arquivo inteiro (ver `escaped_at`);
    sem ele, decide-se pela propria linha, que e uma leitura mais fraca.
    """
    m = _ESCAPE_RE.search(line_text)
    if not m:
        return None
    # o marcador precisa estar dentro de um comentario DE VERDADE
    if em_comentario is None:
        em_comentario = _abre_comentario_fora_de_string(line_text, m.start())
    if not em_comentario:
        return None
    reason = m.group(2)
    # O motivo termina onde o comentario termina. Deixar `.*$` correr ate o
    # fim da linha faria o codigo depois do comentario contar como motivo, e
    # uma excecao vazia passaria por justificada.
    cortes = [reason.find(c) for c in ("*/", "-->") if reason.find(c) >= 0]
    if cortes:
        reason = reason[: min(cortes)]
    reason = reason.strip()
    if len(reason.replace(" ", "")) < MIN_REASON_CHARS:
        return None  # motivo ausente ou simbolico: nao vale como excecao
    scope = m.group(1).strip() if m.group(1) else None
    return Escape(scope=scope or None, reason=reason, line=line_no)


def escaped_at(src: "ScannedSource", line_no: int, guard_id: str) -> Escape | None:
    """
    Escape valido na propria linha (1-based) ou na imediatamente anterior;
    na anterior, so se o comentario estiver sozinho nela (fora ele, a linha
    mascarada so pode ter branco e as chaves de um comentario JSX `{/* */}`).

    Quem decide se o marcador esta em comentario e a varredura lexica do
    ARQUIVO INTEIRO, nao um lexer da linha solta: na linha solta, um apostrofo
    de texto (`don't`) abre uma string que engole o comentario seguinte e anula
    uma excecao legitima, e um `#` ou o `//` de uma URL passam por abridor.
    No texto mascarado, comentario e branco e string nao e -- que e exatamente
    a pergunta.
    """
    for probe in (line_no, line_no - 1):
        if not 1 <= probe <= len(src.lines):
            continue
        linha = src.lines[probe - 1]
        m = _ESCAPE_RE.search(linha)
        if not m:
            continue
        off = src.line_starts[probe - 1] + m.start()
        em_comentario = (off < len(src.masked)
                         and src.masked[off] == " " and linha[m.start()] != " ")
        if probe != line_no and not _so_comentario(src, probe):
            continue  # marcador ao lado de codigo nao alcanca a linha seguinte
        esc = parse_escape(linha, probe, em_comentario=em_comentario)
        if esc and (esc.scope is None or guard_id in esc.scope.split(",")):
            return esc
    return None


def _so_comentario(src: "ScannedSource", linha: int) -> bool:
    """A linha (1-based) nao tem codigo: no texto mascarado sobra so branco e `{}`."""
    ini = src.line_starts[linha - 1]
    fim = src.line_starts[linha] - 1 if linha < len(src.line_starts) else len(src.masked)
    return src.masked[ini:fim].strip(" \t\r{}") == ""


# --------------------------------------------------------------------------
# Varredura lexica de fonte de interface
# --------------------------------------------------------------------------

# Linha de importacao: a declaracao inteira termina no especificador de
# modulo entre aspas (`import X from "x";`, `import "./estilo.css";`,
# `export { X } from "./x";`, `export * from "./x";`, `const x =
# require("x");`), no maximo seguida de `;` e de comentarios. Cada comentario
# de bloco termina no primeiro `*/`: o codigo entre dois deles nao e
# comentario, e a linha que o contem e avaliada. Aceitar qualquer
# linha que comecasse por `export` e contivesse a palavra `from` apagava da
# analise um componente exportado numa linha so com texto "from" ou com o
# utilitario de gradiente `from-*` -- o hifen e fronteira de palavra.
_ESPECIFICADOR = r"""(["'])[^"'\n]+\1"""
_FIM_DE_DECLARACAO = r"\s*;?\s*(?:/\*(?:(?!\*/).)*\*/\s*)*(?://.*)?$"
_IMPORT_RE = re.compile(
    r"^\s*(?:"
    r"import\s+(?:type\s+)?(?:[\w$*{}\s,]+?\s+from\s+)?" + _ESPECIFICADOR
    + r"|export\s+(?:type\s+)?(?:\*(?:\s+as\s+[\w$]+)?|\{[^{}]*\})\s+from\s+"
    + _ESPECIFICADOR.replace(r"\1", r"\2")
    + r"|(?:const|let|var)\s+[\w${},\s]+=\s*require\(\s*"
    + _ESPECIFICADOR.replace(r"\1", r"\3") + r"\s*\)"
    + r")" + _FIM_DE_DECLARACAO)


@dataclass
class Literal:
    """Um literal de string do fonte, com a posicao exata do seu conteudo."""
    start: int          # offset do primeiro caractere do conteudo
    end: int            # offset apos o ultimo caractere do conteudo
    value: str
    line: int           # linha (1-based) onde o conteudo comeca


@dataclass
class ScannedSource:
    text: str
    masked: str                 # comentarios e linhas de import virados em espaco
    literals: list[Literal]
    lines: list[str]
    line_starts: list[int] = field(default_factory=list)

    def line_of(self, offset: int) -> int:
        lo, hi = 0, len(self.line_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.line_starts[mid] <= offset:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1

    def snippet(self, offset: int, width: int = 110) -> str:
        line_no = self.line_of(offset)
        return self.lines[line_no - 1].strip()[:width]


def scan_source(text: str) -> ScannedSource:
    """
    Passada unica que separa string de comentario.

    Precisa ser um lexer de verdade e nao um regex: `"https://x"` contem `//`
    sem ser comentario, e `// cor: "#fff"` contem aspas sem ser literal.
    """
    n = len(text)
    masked = list(text)
    literals: list[Literal] = []
    i = 0
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if c == "/" and nxt == "/":
            j = text.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                masked[k] = " "
            i = j
        elif c == "/" and nxt == "*":
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if masked[k] != "\n":
                    masked[k] = " "
            i = j
        elif c in "\"'`":
            quote = c
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == quote:
                    break
                if quote != "`" and text[j] == "\n":
                    break  # string nao terminada na linha: nao e literal
                j += 1
            if j < n and text[j] == quote:
                literals.append(Literal(start=i + 1, end=j, value=text[i + 1 : j], line=0))
                i = j + 1
            else:
                i += 1
        else:
            i += 1

    line_starts = [0]
    for idx, ch in enumerate(text):
        if ch == "\n":
            line_starts.append(idx + 1)
    lines = text.split("\n")

    scanned = ScannedSource(
        text=text, masked="".join(masked), literals=literals,
        lines=lines, line_starts=line_starts,
    )
    for lit in scanned.literals:
        lit.line = scanned.line_of(lit.start)

    # linhas de import saem da avaliacao
    masked_lines = scanned.masked.split("\n")
    for idx, raw in enumerate(lines):
        if _IMPORT_RE.match(raw):
            masked_lines[idx] = " " * len(masked_lines[idx])
    scanned.masked = "\n".join(masked_lines)
    scanned.literals = [
        lit for lit in scanned.literals if not _IMPORT_RE.match(lines[lit.line - 1])
    ]
    return scanned


def iter_source_files(root: Path, extensions: list[str], ignore_dirs: list[str]):
    """Arquivos varridos, em ordem estavel (determinismo do contrato comum)."""
    if not root.is_dir():
        raise GuardCannotRun(f"diretorio-raiz nao existe ou nao e diretorio: {root}")
    exts = {e if e.startswith(".") else "." + e for e in extensions}
    skip = set(ignore_dirs)
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in skip)
        for name in sorted(filenames):
            if Path(name).suffix in exts:
                found.append(Path(dirpath) / name)
    return sorted(found)


_TAG_NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.\-]*")


def parse_tag(text: str, lt: int) -> tuple[str, int, bool] | None:
    """
    Le a abertura de tag que comeca em `lt` ('<') ate o '>' que a fecha,
    pulando o que esta entre aspas e entre chaves.

    Devolve (nome, posicao desse '>', se a tag fecha em si mesma). Como segue
    ate o '>', le a abertura inteira mesmo quando os atributos ocupam varias
    linhas do fonte.
    """
    m = _TAG_NAME_RE.match(text, lt + 1)
    if not m:
        return None
    name = m.group(0)
    i, depth, n = m.end(), 0, len(text)
    while i < n:
        ch = text[i]
        if ch in "\"'`":
            q, i = ch, i + 1
            while i < n and text[i] != q:
                i += 2 if text[i] == "\\" else 1
            i += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth = max(0, depth - 1)
        elif ch == ">" and depth == 0:
            return name, i, text[max(lt, i - 1)] == "/"
        i += 1
    return None


def enclosing_element(text: str, pos: int, lookback: int = 6000):
    """Elemento cuja regiao de atributos contem `pos`. Alcanca tag multilinha."""
    lt = pos
    floor = max(0, pos - lookback)
    while True:
        lt = text.rfind("<", floor, lt)
        if lt < 0:
            return None
        parsed = parse_tag(text, lt)
        if parsed and lt < pos <= parsed[1]:
            return (lt, *parsed)


def load_config(path: Path) -> dict:
    if path.is_dir():
        raise GuardCannotRun(f"a configuracao aponta para um diretorio, nao para um arquivo: {path}")
    if not path.is_file():
        raise GuardCannotRun(f"arquivo de configuracao ausente: {path}")
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise GuardCannotRun(f"configuracao malformada em {path}: {exc}") from exc
    except OSError as exc:
        raise GuardCannotRun(f"configuracao ilegivel em {path}: {exc}") from exc


# Tipos que uma chave de configuracao pode exigir. O TOML ja entrega o valor
# tipado; o que falta e conferir que e o tipo ESPERADO. Sem isso, o texto
# "false" vira verdadeiro (texto nao vazio) e o texto "slate" vira um
# conjunto de letras -- configuracao errada que sai como aprovacao.
_TIPOS = {
    "texto": lambda v: isinstance(v, str),
    "lista de textos": lambda v: isinstance(v, list) and all(isinstance(x, str) for x in v),
    "tabela": lambda v: isinstance(v, dict),
    "tabela de textos": lambda v: isinstance(v, dict) and all(isinstance(x, str) for x in v.values()),
    "lista de tabelas": lambda v: isinstance(v, list) and all(isinstance(x, dict) for x in v),
    "booleano": lambda v: isinstance(v, bool),
    "inteiro": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "numero": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
}


def check_type(valor, tipo: str, where: str, key: str):
    """Tipo errado e configuracao invalida: 2, nunca um valor reinterpretado."""
    if not _TIPOS[tipo](valor):
        raise GuardCannotRun(
            f"tipo errado na configuracao [{where}] {key}: esperava {tipo}, "
            f"veio {type(valor).__name__} {valor!r}")
    return valor


def require(cfg: dict, key: str, where: str, tipo: str | None = None,
            nao_vazio: bool = False):
    if not isinstance(cfg, dict):
        raise GuardCannotRun(
            f"tipo errado na configuracao [{where}]: esperava tabela, "
            f"veio {type(cfg).__name__} {cfg!r}")
    if key not in cfg:
        raise GuardCannotRun(f"chave obrigatoria ausente na configuracao [{where}]: {key}")
    valor = cfg[key]
    if tipo is not None:
        check_type(valor, tipo, where, key)
    if nao_vazio and not valor:
        raise GuardCannotRun(
            f"chave vazia na configuracao [{where}] {key}: escopo vazio nao e base limpa")
    return valor


def optional(cfg: dict, key: str, where: str, tipo: str, padrao):
    """Chave opcional: ausente vale `padrao`; presente, precisa ter o tipo."""
    if key not in cfg:
        return padrao
    return check_type(cfg[key], tipo, where, key)


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def run_guard(main_fn) -> None:
    """
    Ponto de entrada comum. Garante que falha de execucao vire 2 e nunca 1,
    inclusive erro nao previsto -- um traceback solto sairia com 1 no shell.
    """
    try:
        code = main_fn()
    except GuardCannotRun as exc:
        print(f"NAO CONSIGO EXECUTAR: {exc}", file=sys.stderr)
        sys.exit(EXIT_CANNOT_RUN)
    except Exception as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print(f"NAO CONSIGO EXECUTAR: falha interna do verificador: {exc!r}", file=sys.stderr)
        sys.exit(EXIT_CANNOT_RUN)
    sys.exit(code)
