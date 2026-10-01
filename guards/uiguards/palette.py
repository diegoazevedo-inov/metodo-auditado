"""
GUARD 1 -- Paleta de cores.

Impede que cor literal volte ao codigo de interface depois que as cores do
tema passaram a sair de tokens semanticos. Uma cor literal nao acompanha a
troca de tema: cada uma que entra e um ajuste manual a mais em qualquer tema
novo.

Nove especies detectadas: escala do framework, cor absoluta, hexadecimal,
rgb() literal, hsl() literal, combinacao proibida fundo/texto, classe
malformada com opacidade duplicada, cor de marca como cor de texto, e as
demais notacoes funcionais de cor com valor literal -- oklch(), oklab(),
lab(), lch(), hwb() e color() --, reunidas numa especie so.

CODIGOS DE SAIDA: 0 limpo | 1 achei violacao | 2 nao consigo executar.

LIMITACOES DECLARADAS -- o que este guard NAO cobre:
  * O fonte e lido por uma varredura lexica que separa codigo, comentario e
    string; nao ha arvore sintatica nem parser de JSX. Por isso TEXTO de
    marcacao que contenha `//` -- uma URL escrita como texto, por exemplo --
    passa por comentario dali ate o fim da linha: um marcador de excecao
    escrito depois disso, na mesma linha, isenta, e as classes declaradas
    depois disso, na mesma linha, somem da analise. Aspa ou apostrofo em
    TEXTO de marcacao tambem abre string para essa varredura, que a fecha na
    proxima aspa igual da mesma linha: o trecho entre as duas troca de lado,
    e uma classe dessa linha pode sumir da analise
    (`<p>Clique em "Salvar</p><span className="text-red-500">` nao acusa).
    Template literal ANINHADO dentro de outro (`${cond ? `bg-red-500` : ""}`
    dentro de crases) tambem engana a varredura: ela fecha o literal externo
    na crase interna, e as classes do literal de dentro ficam fora de
    qualquer literal -- as especies 1, 2, 6, 7 e 8 nao as veem. Hex e
    notacao funcional continuam achados ali, porque sao procurados no codigo
    inteiro.
  * Linha de importacao nao e avaliada, e e reconhecida pela forma inteira:
    `import ...`, `export ... from` ou `require(...)` terminando no
    especificador de modulo entre aspas, no maximo com `;` e comentarios
    depois; cada comentario de bloco termina no primeiro `*/`, e codigo entre
    dois deles faz a linha ser avaliada. Uma importacao escrita em varias
    linhas tem avaliadas as linhas
    que nao terminam no especificador -- so nomes, sem cor. Duas declaracoes
    na mesma linha (`import ...; export const X = ...`) nao sao importacao, e
    a linha inteira e avaliada, o especificador incluido.
  * A correlacao entre classes (especie 6) so acontece dentro de UM MESMO
    literal de string. Classe formada por concatenacao ou interpolacao, ou
    trazida de outro modulo, nao entra no par; e fundo declarado num elemento
    com cor de texto declarada num descendente dele e combinacao que este
    guard nao ve.
  * Na especie 6, `text-[..]` conta como cor de texto, salvo quando o valor
    e MEDIDA: numero com ou sem unidade (`text-[13px]`, `text-[1.2rem]`),
    `calc()`/`clamp()`/`min()`/`max()`, ou a dica `length:`. Qualquer outro
    valor arbitrario -- `text-[var(--x)]` inclusive, que o framework pode ler
    como tamanho -- e tratado como cor: ao lado de um fundo solido de papel
    semantico, e acusado.
  * Variante de estado (hover:, focus:, dark:) so e posta ao lado do fundo
    quando o prefixo do texto contem o prefixo do fundo; fora disso, o
    estado nunca e confrontado com a classe sem variante.
  * Variante de pseudo-elemento so conta como texto na especie 8 se estiver
    em `variantes_rotulo` da configuracao (neste projeto, `file` e
    `placeholder`). `before:`/`after:` com texto posto por `content-[..]` e a
    cor da marca passam enquanto nao forem acrescentadas la.
  * Para a especie 8, textual e o elemento que traz texto LITERAL no corpo.
    Se o unico texto chega por expressao ou por traducao resolvida em
    runtime, o elemento passa como se nao tivesse texto, so icone. E so e
    avaliado o literal que esta dentro da abertura de uma tag: classe guardada
    em variavel e aplicada depois (`className={titulo}`) nao chega a elemento
    nenhum, e a especie 8 nao a ve.
  * Notacao funcional de cor e reconhecida por dez nomes: rgb(), rgba(),
    hsl(), hsla(), oklch(), oklab(), lab(), lch(), hwb() e color(). Cor por
    nome passa (`color: "red"` em estilo em linha, `text-[tomato]`). So e
    acusado o argumento que comeca por numero -- em color(), por nome de
    espaco de cor seguido de numero --; a sintaxe relativa (`oklch(from red
    l c h)`) nao e classificada. A notacao cujos primeiros doze caracteres
    de argumento contem `var(` e tratada como referencia a variavel:
    `rgb(0 0 0 / var(--a))` passa com a cor literal dentro.
  * Hexadecimal logo depois de `href=`, `to=`, `id=`, `for=` ou
    `aria-controls=` e tratado como ancora de navegacao e passa
    (`to="#ff0000"` e `id="#123456"` nao acusam), assim como o que vem
    depois de `://` ou de `/` na mesma palavra.
  * O que nao e arquivo de componente varrido fica de fora: folha de
    estilo, tema compilado, SVG externo e recurso de terceiro nao sao lidos.
  * O motivo da excecao tem piso de FORMA, nao de sentido: no marcador em
    comentario, dez caracteres nao brancos bastam; na allowlist, dez
    caracteres depois de aparar as pontas, com os espacos internos contando.
    O formato recusa excecao vazia ou simbolica, nao excecao mal justificada
    -- isso e trabalho de quem revisa. O marcador vale para a propria linha;
    para a linha seguinte, so quando esta sozinho na dele (sem codigo ao
    lado).
  * A allowlist "so pode diminuir" NAO e imposta: o guard nao compara com
    uma versao anterior e aceita entrada nova com motivo. Ele so avisa, sem
    reprovar, a entrada que nao casa arquivo nenhum. Segurar o tamanho da
    lista e trabalho de quem revisa o diff da configuracao.
  * Nao mede contraste. Um par de tokens semanticos ilegivel passa aqui e e
    assunto do GUARD 3.
  * `cores_marca` vazia desliga a especie 8, `fundo_texto` vazio desliga a
    especie 6, e `tokens_semanticos` vazio desliga as duas, sem aviso: o
    guard sai limpo por nao ter o que procurar. So `familias`,
    `prefixos_cor` e `extensoes` vazias sao recusadas com 2.
  RECURSO COMPLEMENTAR para o que fica descoberto: GUARD 3 para contraste
  calculado, e inspecao visual dos dois temas para classe dinamica.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from .common import (
    EXIT_CLEAN, EXIT_VIOLATION, GuardCannotRun, ScannedSource,
    enclosing_element, escaped_at, iter_source_files, load_config, optional,
    parse_tag, rel, require, run_guard, scan_source,
)

GUARD_ID = "paleta"

ESPECIES = {
    "escala-framework": (
        "Cor de escala do framework",
        "trocar pelo token semantico equivalente (ex.: text-muted-foreground, bg-card)",
    ),
    "cor-absoluta": (
        "Cor absoluta (branco/preto por utilitario)",
        "usar o token do papel: bg-background / text-foreground / bg-card",
    ),
    "hex-literal": (
        "Hexadecimal literal",
        "mover o valor para um token de tema e referenciar o token",
    ),
    "rgb-literal": (
        "Notacao funcional RGB literal",
        "trocar por rgb(var(--token)), ou pela classe do token de tema",
    ),
    "hsl-literal": (
        "Notacao funcional HSL literal",
        "trocar por hsl(var(--token)), ou pela classe do token de tema",
    ),
    "combinacao-proibida": (
        "Fundo solido de papel semantico com texto que nao e o token de contraste",
        "usar o token de texto que a config associa a esse fundo, e nenhum outro",
    ),
    "classe-malformada": (
        "Modificador de opacidade duplicado",
        "manter um unico modificador: com dois, a classe nao produz cor nenhuma",
    ),
    "marca-como-texto": (
        "Cor de marca aplicada como cor de texto",
        "manter a marca em icone ou borda; para texto usar text-foreground",
    ),
    "cor-funcional-moderna": (
        "Notacao funcional de cor literal alem de RGB/HSL (oklch, oklab, lab, lch, hwb, color)",
        "mover o valor para um token de tema e referenciar o token, ex.: oklch(var(--token))",
    ),
}
ORDEM_ESPECIES = list(ESPECIES)


@dataclass(frozen=True)
class Achado:
    especie: str
    arquivo: str
    linha: int
    trecho: str
    detalhe: str

    def chave(self):
        return (ORDEM_ESPECIES.index(self.especie), self.arquivo, self.linha,
                self.trecho, self.detalhe)


# ---------------------------------------------------------------------------
# Tokenizacao de classe utilitaria
# ---------------------------------------------------------------------------

def split_class_tokens(value: str) -> list[tuple[str, int]]:
    """Quebra um literal em tokens de classe, devolvendo (token, offset)."""
    out, buf, start, depth = [], [], 0, 0
    for idx, ch in enumerate(value):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth = max(0, depth - 1)
        if ch.isspace() and depth == 0:
            if buf:
                out.append(("".join(buf), start))
                buf = []
        else:
            if not buf:
                start = idx
            buf.append(ch)
    if buf:
        out.append(("".join(buf), start))
    return out


def split_variants(token: str) -> tuple[list[str], str]:
    """Separa prefixos de variante da base. `:` dentro de [..] nao separa."""
    parts, buf, depth = [], [], 0
    for ch in token:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth = max(0, depth - 1)
        if ch == ":" and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    # O marcador de prioridade e prefixo numa versao do framework e SUFIXO na
    # seguinte (`!bg-red-500` e `bg-red-500!`). Tirar so o da esquerda deixava
    # a forma nova escapar inteira -- mesma cor, mesma divida, um caractere de
    # lugar diferente.
    base = parts[-1].strip("!")
    return parts[:-1], base


def split_opacity(base: str) -> tuple[str, list[str]]:
    """Separa o utilitario dos modificadores de opacidade (fora de [..])."""
    segs, buf, depth = [], [], 0
    for ch in base:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth = max(0, depth - 1)
        if ch == "/" and depth == 0:
            segs.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    segs.append("".join(buf))
    return segs[0], segs[1:]


# ---------------------------------------------------------------------------
# Contexto de elemento (especie 8)
# ---------------------------------------------------------------------------

def has_literal_text(text: str, name: str, gt: int, self_closing: bool) -> bool:
    """
    Existe conteudo textual literal dentro do elemento?

    Ignora regioes de tag aninhada (atributos como aria-label nao sao texto
    renderizado) e expressoes {..}. O que sobra sao nos de texto.
    """
    if self_closing:
        return False
    n = len(text)
    i, depth = gt + 1, 1
    body: list[str] = []
    open_re = re.compile(r"<\s*" + re.escape(name) + r"[\s/>]")
    close_re = re.compile(r"</\s*" + re.escape(name) + r"\s*>")
    while i < n and depth > 0:
        ch = text[i]
        if ch == "<":
            if close_re.match(text, i):
                depth -= 1
                if depth == 0:
                    break
                i = close_re.match(text, i).end()
                continue
            if open_re.match(text, i):
                depth += 1
            parsed = parse_tag(text, i)
            if parsed:
                i = parsed[1] + 1
            elif text[i + 1 : i + 2] == "/":
                fim = text.find(">", i)          # fechamento de tag aninhada
                i = (fim + 1) if fim >= 0 else i + 1
            else:
                i += 1
            continue
        if ch == "{":
            b, j = 1, i + 1
            while j < n and b:
                if text[j] == "{":
                    b += 1
                elif text[j] == "}":
                    b -= 1
                j += 1
            i = j
            continue
        body.append(ch)
        i += 1
    return bool("".join(body).strip())


# ---------------------------------------------------------------------------
# Verificador
# ---------------------------------------------------------------------------

class VerificadorPaleta:
    def __init__(self, cfg: dict, raiz_projeto: Path):
        p = require(cfg, "paleta", "raiz", "tabela")
        proj = require(cfg, "projeto", "raiz", "tabela")
        self.raiz_projeto = raiz_projeto
        self.raiz_ui = (raiz_projeto / require(proj, "raiz_ui", "projeto", "texto")).resolve()
        self.extensoes = require(proj, "extensoes", "projeto", "lista de textos", nao_vazio=True)
        self.ignorar = optional(proj, "ignorar_dirs", "projeto", "lista de textos", [])
        # Tipo conferido chave a chave: `familias = "slate"`, texto no lugar de
        # lista, virava o conjunto de letras {s, l, a, t, e} e a especie 1
        # deixava de achar qualquer cor -- sem erro nenhum.
        self.familias = set(require(p, "familias", "paleta", "lista de textos", nao_vazio=True))
        self.prefixos = set(require(p, "prefixos_cor", "paleta", "lista de textos", nao_vazio=True))
        self.semanticos = set(require(p, "tokens_semanticos", "paleta", "lista de textos"))
        self.marcas = set(require(p, "cores_marca", "paleta", "lista de textos"))
        self.variantes_rotulo = set(optional(p, "variantes_rotulo", "paleta", "lista de textos", []))
        self.fundo_texto = dict(require(p, "fundo_texto", "paleta", "tabela de textos"))
        self.isentos = dict(optional(p, "isentos", "paleta", "tabela de textos", {}))
        for arquivo, motivo in self.isentos.items():
            if len(motivo.strip()) < 10:
                raise GuardCannotRun(
                    f"allowlist sem motivo escrito para '{arquivo}': "
                    "toda isencao precisa declarar o motivo"
                )
        self.achados: list[Achado] = []
        self.arquivos_varridos = 0
        self.isentos_vistos: list[str] = []

    # -- classificacao de token -------------------------------------------
    # Valor arbitrario de `text-[..]` que e MEDIDA, e portanto tamanho de
    # fonte, nao cor: numero com ou sem unidade, funcao de calculo de medida,
    # ou a dica explicita `length:`. Tratar todo `text-[..]` como cor fazia
    # `text-[13px]` ao lado do token certo sair como combinacao proibida.
    _MEDIDA = re.compile(
        r"^\[(?:length:.*|-?\d*\.?\d+(?:px|r?em|%|v[wh]|[sdl]v[wh]|vmin|vmax|pt|pc|ch|ex|r?lh|cq[whib])?"
        r"|(?:calc|clamp|min|max)\(.*)\]$")

    def _eh_cor_de_texto(self, util: str) -> bool:
        if not util.startswith("text-"):
            return False
        resto = util[5:]
        if resto.startswith("["):
            return not self._MEDIDA.match(resto)
        if resto in self.semanticos or resto in ("white", "black"):
            return True
        m = re.match(r"^([a-z]+)-(\d{1,3})$", resto)
        return bool(m and m.group(1) in self.familias)

    # Segmento de lado ou eixo que o framework aceita entre o prefixo de
    # propriedade e a cor: border-b-*, divide-x-*, border-s-*. Partir o
    # utilitario so no primeiro hifen fazia `border-red-500` ser pego e
    # `border-b-red-500` escapar -- mesma cor, mesma divida, uma letra de
    # diferenca.
    _LADOS = frozenset({"x", "y", "t", "b", "l", "r", "s", "e"})

    def _separar_prefixo(self, util: str) -> tuple[str, str] | None:
        """(prefixo de cor, resto) ou None se o utilitario nao aceita cor."""
        segs = util.split("-")
        # prefixo composto declarado na configuracao (ex.: ring-offset)
        if len(segs) >= 3 and "-".join(segs[:2]) in self.prefixos:
            return "-".join(segs[:2]), "-".join(segs[2:])
        if segs[0] not in self.prefixos:
            return None
        if len(segs) >= 3 and segs[1] in self._LADOS:
            return segs[0], "-".join(segs[2:])
        return segs[0], "-".join(segs[1:])

    def _add(self, especie, arquivo, linha, trecho, detalhe):
        self.achados.append(Achado(especie, arquivo, linha, trecho, detalhe))

    # -- varredura de um arquivo -------------------------------------------
    def verificar_arquivo(self, path: Path):
        arquivo = rel(path, self.raiz_projeto)
        chave_isencao = rel(path, self.raiz_ui)
        if chave_isencao in self.isentos:
            self.isentos_vistos.append(chave_isencao)
            return
        try:
            texto = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise GuardCannotRun(f"nao consigo ler {arquivo}: {exc}") from exc
        self.arquivos_varridos += 1
        src = scan_source(texto)
        self._especies_de_classe(src, arquivo)
        self._especies_de_notacao(src, arquivo)

    # especies 1, 2, 6, 7, 8 -- percorrem cada literal de string do arquivo
    def _especies_de_classe(self, src: ScannedSource, arquivo: str):
        for lit in src.literals:
            if src.masked[lit.start : lit.end].strip() == "":
                continue  # literal dentro de comentario ou linha de import
            tokens = split_class_tokens(lit.value)
            if not tokens:
                continue
            fundos, textos = [], []
            for tok, off in tokens:
                linha = src.line_of(lit.start + off)
                variantes, base = split_variants(tok)
                util, opac = split_opacity(base)
                if "-" not in util:
                    continue
                separado = self._separar_prefixo(util)
                prefixo, resto = separado if separado else (None, "")
                escapou = escaped_at(src, linha, GUARD_ID)

                # especie 7 -- modificador de opacidade duplicado
                if len(opac) > 1:
                    if not escapou:
                        self._add("classe-malformada", arquivo, linha, tok,
                                  f"{len(opac)} modificadores de opacidade no mesmo utilitario")
                    continue

                if prefixo is not None:
                    # especie 1 -- escala do framework
                    m = re.match(r"^([a-z]+)-(\d{1,3})$", resto)
                    if m and m.group(1) in self.familias:
                        if not escapou:
                            self._add("escala-framework", arquivo, linha, tok,
                                      f"familia '{m.group(1)}' grau {m.group(2)}")
                    # especie 2 -- cor absoluta
                    elif resto in ("white", "black"):
                        if not escapou:
                            self._add("cor-absoluta", arquivo, linha, tok,
                                      f"'{resto}' aplicado por utilitario")

                if util in self.fundo_texto:
                    fundos.append((util, set(variantes), linha, tok))
                if self._eh_cor_de_texto(util):
                    textos.append((util, set(variantes), linha, tok, off))
                    # especie 8 -- cor de marca como cor de texto
                    if util[5:].split("/")[0] in self.marcas:
                        self._especie_marca(src, lit, off, tok, linha, variantes, arquivo)

            # especie 6 -- combinacao proibida. Fundo e texto so formam par
            # quando vem do mesmo literal: numa condicional com duas
            # alternativas na mesma linha, um lado nao contamina o outro.
            for fundo, vfundo, lfundo, tfundo in fundos:
                exigido = self.fundo_texto[fundo]
                for texto, vtexto, ltexto, ttexto, _off in textos:
                    if not vfundo <= vtexto:
                        continue  # variantes nao correlacionadas
                    if texto != exigido:
                        linha = min(lfundo, ltexto)
                        if escaped_at(src, linha, GUARD_ID):
                            continue
                        self._add("combinacao-proibida", arquivo, linha,
                                  f"{tfundo} ... {ttexto}",
                                  f"'{fundo}' exige exatamente '{exigido}'")

    def _especie_marca(self, src, lit, off, tok, linha, variantes, arquivo):
        if escaped_at(src, linha, GUARD_ID):
            return
        # variante de pseudo-elemento que desenha texto conta como texto
        if set(variantes) & self.variantes_rotulo:
            self._add("marca-como-texto", arquivo, linha, tok,
                      "variante de pseudo-elemento que desenha texto")
            return
        ctx = enclosing_element(src.text, lit.start + off)
        if ctx is None:
            return
        lt, nome, gt, autofechada = ctx
        if not has_literal_text(src.text, nome, gt, autofechada):
            return  # elemento sem texto, so icone: fica fora da especie 8
        self._add("marca-como-texto", arquivo, linha, tok,
                  f"<{nome}> com conteudo textual literal")

    # especies 3, 4, 5, 9 -- notacao de cor em qualquer posicao do codigo
    def _especies_de_notacao(self, src: ScannedSource, arquivo: str):
        m = src.masked
        for match in re.finditer(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})(?![0-9a-zA-Z_])", m):
            ini = max(0, match.start() - 200)
            antes = m[ini:match.start()]
            if re.search(r"(?:href|to|id|for|aria-controls)\s*=\s*[\"'{]?\s*$", antes):
                continue  # ancora de navegacao, nao cor
            palavra = re.split(r"[\s\"'`(,;]", antes)[-1]
            if "://" in palavra or palavra.startswith("/"):
                continue  # fragmento de URL, nao cor
            linha = src.line_of(match.start())
            if escaped_at(src, linha, GUARD_ID):
                continue
            self._add("hex-literal", arquivo, linha, src.snippet(match.start()),
                      match.group(0))

        # Valor arbitrario do framework une as partes com `_`, como em
        # `shadow-[0_0_0_rgb(0,0,0)]`. Para o regex `_` e caractere de
        # palavra, e exigir `\b` antes do nome deixaria esse rgb() passar. A
        # condicao abaixo so recusa o nome colado a letra, digito ou hifen.
        # O mesmo lookbehind impede que `lab(` seja achado dentro de `oklab(`.
        # color() abre com o nome do espaco de cor (`color(display-p3 1 0 0)`),
        # por isso o literal dele e um identificador seguido de numero.
        literal_numerico = r"^\s*[-.\d]"
        literal_de_color = r"^\s*[A-Za-z][\w-]*[\s_]+[-.\d]"
        for nome, especie, literal in (
            ("rgba?", "rgb-literal", literal_numerico),
            ("hsla?", "hsl-literal", literal_numerico),
            ("oklch|oklab|lab|lch|hwb", "cor-funcional-moderna", literal_numerico),
            ("color", "cor-funcional-moderna", literal_de_color),
        ):
            # CSS nao distingue caixa: RGB( e rgb( sao a mesma notacao.
            padrao = re.compile(r"(?<![A-Za-z0-9\-])(" + nome + r")\(\s*([^)]*)", re.IGNORECASE)
            for match in padrao.finditer(m):
                args = match.group(2)
                # referencia a variavel dentro da notacao NAO e violacao
                if re.match(r"^\s*var\s*\(", args) or "var(" in args[:12]:
                    continue
                if not re.match(literal, args):
                    continue  # nem literal nem var(): nao classifico
                linha = src.line_of(match.start())
                if escaped_at(src, linha, GUARD_ID):
                    continue
                self._add(especie, arquivo, linha, src.snippet(match.start()),
                          f"{match.group(1)}({args.strip()[:40]}...)")

    # -- execucao ----------------------------------------------------------
    def executar(self) -> int:
        arquivos = iter_source_files(self.raiz_ui, self.extensoes, self.ignorar)
        if not arquivos:
            raise GuardCannotRun(
                f"nenhum arquivo com extensoes {self.extensoes} sob {self.raiz_ui}: "
                "escopo vazio nao e base limpa"
            )
        for path in arquivos:
            self.verificar_arquivo(path)
        return self.relatar()

    def relatar(self) -> int:
        print("GUARD 1 -- paleta de cores")
        print(f"raiz varrida: {rel(self.raiz_ui, self.raiz_projeto)}")
        if self.isentos_vistos:
            print("\nisencoes aplicadas (allowlist, com motivo):")
            for arq in sorted(self.isentos_vistos):
                print(f"  - {arq}: {self.isentos[arq]}")
        # Entrada da allowlist que nao corresponde a nenhum arquivo varrido e
        # avisada pelo nome, para a lista nao acumular isencao sem uso. Nao
        # reprova: nao e violacao de cor.
        mortas = sorted(set(self.isentos) - set(self.isentos_vistos))
        if mortas:
            print("\nAVISO -- entradas da allowlist que nao casaram arquivo nenhum:")
            for arq in mortas:
                print(f"  - {arq}: {self.isentos[arq]}")
            print("  a lista so pode encolher: remova o que nao existe mais.")
        if not self.achados:
            print(f"\nLIMPO: {self.arquivos_varridos} arquivos varridos, 0 violacoes.")
            return EXIT_CLEAN

        por_especie: dict[str, list[Achado]] = {}
        for a in sorted(self.achados, key=Achado.chave):
            por_especie.setdefault(a.especie, []).append(a)
        for especie in ORDEM_ESPECIES:
            grupo = por_especie.get(especie)
            if not grupo:
                continue
            titulo, dica = ESPECIES[especie]
            print(f"\n[{especie}] {titulo} -- {len(grupo)} ocorrencia(s)")
            print(f"  correcao: {dica}")
            for a in grupo:
                print(f"    {a.arquivo}:{a.linha}: {a.trecho}")
                print(f"      ^ {a.detalhe}")
        print(f"\nTOTAL: {len(self.achados)} violacoes em "
              f"{len({a.arquivo for a in self.achados})} arquivo(s); "
              f"{self.arquivos_varridos} arquivos varridos.")
        return EXIT_VIOLATION


def main() -> int:
    ap = argparse.ArgumentParser(description="GUARD 1 -- paleta de cores")
    ap.add_argument("--config", default="guards.toml")
    args = ap.parse_args()
    cfg_path = Path(args.config).resolve()
    cfg = load_config(cfg_path)
    return VerificadorPaleta(cfg, cfg_path.parent).executar()


if __name__ == "__main__":
    run_guard(main)
