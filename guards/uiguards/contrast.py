"""
GUARD 3 -- Contraste computado.

Calcula a razao de contraste de cada par declarado e compara com o minimo da
norma. A decisao e NUMERICA: uma combinacao pode parecer legivel e ainda
assim ficar abaixo do minimo.

Le os dois blocos de tokens do arquivo de estilo global (tema base e tema
alternativo), monta o tema alternativo pela UNIAO com o base -- o que o
alternativo nao sobrescreve vem do base -- e calcula a razao de cada par.

Minimos vindos da norma de acessibilidade (WCAG 2.x), nao de escolha do
projeto:
    texto corrente ............................. 4.5:1
    elemento de interface, indicador de foco
    e texto de dica ............................ 3.0:1

CODIGOS DE SAIDA: 0 limpo | 1 achei violacao | 2 nao consigo executar.
Bloco de tokens nao encontrado e 2. Valor de cor em formato inesperado e 2 --
nao consigo calcular, e isso jamais pode virar aprovacao. Cor com alfa
diferente de 1 tambem e 2, com o token nomeado: a cor efetiva depende do que
esta atras dela, e isso o guard nao sabe.
Canal fora da faixa que o formato admite -- rgb() acima de 255, saturacao ou
luminosidade acima de 100% -- tambem e 2: a razao calculada dele difere da que a
tela mostra. Chave da tabela de pares com tipo errado (`informativo` que nao e
booleano, rotulo que nao e texto) e 2.
Token ausente REPROVA (1) e nunca passa por omissao, salvo par informativo.
A ultima declaracao de um bloco pode vir sem `;`, como o CSS permite.

LIMITACOES DECLARADAS -- o que este guard NAO cobre:
  * Avalia os pares DECLARADOS na tabela, e apenas eles. Combinacao que
    acontece na tela e nao esta na tabela nao e vista. A tabela e curadoria
    humana, e essa e a maior fragilidade do guard.
  * Le apenas os dois blocos de tokens nomeados, e SO no nivel de topo da
    folha. Token redefinido em um terceiro tema ou em escopo de componente
    nao entra na uniao e nao e visto.
    Sobre regra-arroba (@media/@supports/@layer), a conduta e RECUSAR, nao
    ignorar: se o seletor do tema so aparece aninhado, o guard sai com 2; se
    aparece mais de uma vez no topo, tambem. O guard nao escolhe entre dois
    blocos candidatos -- escolher errado aprovaria um tema que nao e o que
    aplica na tela. Um bloco aninhado que redefina token POR CIMA de um bloco
    de topo valido continua invisivel: essa parte segue nao coberta.
    Dentro do bloco do tema, regra aninhada (CSS nesting) aplica a
    DESCENDENTES e NAO entra na uniao -- o bloco e lido inteiro, mas so as
    declaracoes do proprio seletor contam.
  * O casamento do seletor e por ocorrencia do texto declarado, entao uma
    regra que apenas CONTENHA o seletor (`.dark .cartao { }`, `html.dark { }`)
    conta como bloco daquele tema: com o bloco real presente viram "dois
    blocos no topo" e o guard recusa (2); sozinha, ela e lida como se fosse o
    tema. Mantenha o seletor de tema em uma unica regra de topo.
  * Assume fundo OPACO. Nao resolve transparencia, gradiente, imagem de
    fundo, sombra nem sobreposicao -- casos em que a cor efetiva nao e a
    declarada. O alfa escrito no proprio valor (quarto argumento de
    rgba()/hsla(), ou depois de `/` em rgb()/hsl()) nao e calculado: abaixo
    de 1 o guard recusa (2). Transparencia aplicada por outra via -- opacidade
    do elemento, camadas sobrepostas -- nao passa pelos tokens e nao e vista.
  * Nao sabe o tamanho da fonte renderizada: usa a categoria declarada na
    tabela. Texto grande, que a norma trata com minimo menor, e classificado
    a mao por quem escreve a tabela.
  * Contraste aprovado nao e legibilidade garantida: espacamento, peso da
    fonte e daltonismo ficam fora.
  RECURSO COMPLEMENTAR para o que fica descoberto: inspecao visual dos dois temas
  e teste com pessoa usuaria; a tabela so cobre o que alguem lembrou de por.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from .common import (
    EXIT_CLEAN, EXIT_VIOLATION, GuardCannotRun, check_type, load_config, require,
    run_guard,
)

# Minimos da norma. Nao sao configuraveis por projeto.
MINIMOS = {"texto": 4.5, "interface": 3.0}


# ---------------------------------------------------------------------------
# Cor -> luminancia relativa -> razao de contraste (WCAG 2.x)
# ---------------------------------------------------------------------------

def _hsl_para_rgb(h: float, s: float, l: float) -> tuple[float, float, float]:
    h = h % 360.0
    s, l = s / 100.0, l / 100.0
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60.0) % 2 - 1))
    m = l - c / 2
    seg = int(h // 60) % 6
    r, g, b = [(c, x, 0), (x, c, 0), (0, c, x), (0, x, c), (x, 0, c), (c, 0, x)][seg]
    return (r + m) * 255, (g + m) * 255, (b + m) * 255


def _exigir_opaco(alfa: str | None, valor: str, contexto: str) -> None:
    """
    Alfa ausente ou exatamente 1 (ou 100%) e cor opaca. Alfa abaixo de 1
    deixa ver o que esta atras, e o guard nao sabe o que esta atras: a cor
    efetiva nao e a declarada e a razao nao se calcula. Isso e 2 -- nunca a
    cor tratada como opaca e aprovada.
    """
    if alfa is None:
        return
    m = re.fullmatch(r"(\d*\.?\d+)(%?)", alfa.strip())
    if not m:
        raise GuardCannotRun(
            f"formato de cor inesperado em {contexto}: {valor!r} (alfa {alfa.strip()!r}). "
            "Nao consigo calcular -- e isso nunca vira aprovacao.")
    a = float(m.group(1)) / (100.0 if m.group(2) else 1.0)
    if a == 1.0:
        return
    raise GuardCannotRun(
        f"cor com alfa {alfa.strip()} em {contexto}: {valor!r}. Com alfa diferente "
        "de 1 a cor efetiva depende do que esta atras, e a razao nao se calcula. "
        "Nao consigo calcular -- e isso nunca vira aprovacao.")


_NUMERO = re.compile(r"\d*\.?\d+")


def _canais(brutos, maximos, valor: str, contexto: str) -> list[float]:
    """
    Numeros dos canais, cada um DENTRO da faixa que o formato admite.

    Fora da faixa -- `rgb(300, 300, 300)`, luminosidade de 150% -- a
    luminancia passa de 1 e a razao infla: o par sai aprovado com uma razao
    que a tela nao mostra. Nao consigo calcular a cor que a tela mostra a
    partir de um valor assim, e isso e 2, nunca aprovacao.
    """
    out = []
    for bruto, maximo in zip(brutos, maximos):
        if not _NUMERO.fullmatch(bruto):
            raise GuardCannotRun(
                f"formato de cor inesperado em {contexto}: {valor!r} (numero {bruto!r}). "
                "Nao consigo calcular -- e isso nunca vira aprovacao.")
        n = float(bruto)
        if maximo is not None and n > maximo:
            raise GuardCannotRun(
                f"valor de cor fora da faixa em {contexto}: {valor!r} ({bruto} passa de "
                f"{maximo:g}). Nao consigo calcular a cor que a tela mostra -- e isso "
                "nunca vira aprovacao.")
        out.append(n)
    return out


def parse_cor(valor: str, contexto: str) -> tuple[float, float, float]:
    """Formatos aceitos: hex, rgb(), hsl() e a tripla HSL nua `H S% L%`.
    Alfa no valor so e aceito quando e exatamente 1 (opaco). Canal fora da
    faixa (rgb acima de 255, saturacao ou luminosidade acima de 100%) e 2."""
    v = valor.strip().rstrip(";").strip()

    m = re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", v)
    if m:
        d = m.group(1)
        if len(d) == 3:
            d = "".join(ch * 2 for ch in d)
        return tuple(int(d[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]

    m = re.fullmatch(r"rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)\s*(?:[,/]([^)]*))?\)", v)
    if m:
        _exigir_opaco(m.group(4), valor, contexto)
        return tuple(_canais(m.groups()[:3], (255, 255, 255), valor, contexto))  # type: ignore[return-value]

    m = re.fullmatch(r"hsla?\(\s*([-\d.]+)(?:deg)?[\s,]+([\d.]+)%[\s,]+([\d.]+)%\s*(?:[,/]([^)]*))?\)", v)
    if m:
        _exigir_opaco(m.group(4), valor, contexto)
        h = float(m.group(1)) if re.fullmatch(r"-?\d*\.?\d+", m.group(1)) else None
        if h is None:
            raise GuardCannotRun(
                f"formato de cor inesperado em {contexto}: {valor!r}. "
                "Nao consigo calcular -- e isso nunca vira aprovacao.")
        return _hsl_para_rgb(h, *_canais(m.groups()[1:3], (100, 100), valor, contexto))

    # tripla HSL nua, convencao dos temas com `hsl(var(--token))`
    m = re.fullmatch(r"(-?\d*\.?\d+)\s+([\d.]+)%\s+([\d.]+)%", v)
    if m:
        return _hsl_para_rgb(float(m.group(1)),
                             *_canais(m.groups()[1:], (100, 100), valor, contexto))

    raise GuardCannotRun(
        f"formato de cor inesperado em {contexto}: {valor!r}. "
        "Nao consigo calcular -- e isso nunca vira aprovacao.")


def luminancia(rgb: tuple[float, float, float]) -> float:
    def canal(c: float) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (canal(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def razao(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    la, lb = luminancia(a), luminancia(b)
    claro, escuro = max(la, lb), min(la, lb)
    return (claro + 0.05) / (escuro + 0.05)


# ---------------------------------------------------------------------------
# Extracao dos blocos de token
# ---------------------------------------------------------------------------

def mascarar_comentarios(css: str) -> str:
    """Comentario vira espaco, mantendo as posicoes. O seletor citado num
    comentario deixa de existir para a busca: so seletor de codigo abre bloco."""
    out, i, n = list(css), 0, len(css)
    while i < n:
        if css[i] == "/" and css[i + 1 : i + 2] == "*":
            fim = css.find("*/", i + 2)
            fim = n if fim < 0 else fim + 2
            for k in range(i, fim):
                if out[k] != "\n":
                    out[k] = " "
            i = fim
        else:
            i += 1
    return "".join(out)


def _profundidade_ate(limpo: str, pos: int) -> int:
    """Quantas chaves estao abertas em `pos`. Zero = nivel de topo da folha."""
    return limpo.count("{", 0, pos) - limpo.count("}", 0, pos)


def extrair_bloco(css: str, seletor: str, arquivo: Path) -> dict[str, str]:
    """
    Devolve os tokens do bloco do seletor, lido INTEIRO mesmo quando ha
    chaves aninhadas dentro dele.

    SO ACEITA BLOCO NO NIVEL DE TOPO da folha de estilo. Um bloco de mesmo
    seletor aninhado dentro de uma regra-arroba (`@media`, `@supports`,
    `@layer`) NAO serve como se fosse o bloco do tema: ele vale so sob a
    condicao da regra, e engoli-lo em silencio faria o guard avaliar tokens
    que nao sao os que aplicam. Pior: se o aninhado vier ANTES do bloco real
    no arquivo, uma leitura ingenua le o aninhado e IGNORA o verdadeiro --
    aprovando um tema ilegivel. Aqui isso vira recusa (2), nunca aprovacao.

    Mais de um bloco de topo com o mesmo seletor tambem e recusa: qual dos
    dois manda depende de ordem e de especificidade, e adivinhar seria
    exatamente o silencio que este guard existe para nao produzir.
    """
    limpo = mascarar_comentarios(css)
    de_topo: list[tuple[int, int]] = []   # (inicio do corpo, fim do corpo)
    aninhados = 0
    for m in re.finditer(re.escape(seletor) + r"(?![\w-])", limpo):
        j = m.end()
        # entre o seletor e a chave so pode haver mais seletor
        while j < len(limpo) and limpo[j] not in "{;}":
            if limpo[j] not in " \t\r\n,.#[]=\"'*>+~:_-" and not limpo[j].isalnum():
                break
            j += 1
        if j >= len(limpo) or limpo[j] != "{":
            continue
        profundidade, k = 1, j + 1
        while k < len(limpo) and profundidade:
            if limpo[k] == "{":
                profundidade += 1
            elif limpo[k] == "}":
                profundidade -= 1
            k += 1
        if profundidade:
            raise GuardCannotRun(f"bloco '{seletor}' sem fechamento balanceado em {arquivo}")
        profundidade_no_seletor = _profundidade_ate(limpo, m.start())
        if profundidade_no_seletor == 0:
            de_topo.append((j + 1, k - 1))
        elif profundidade_no_seletor < 0:
            # Mais fechamentos que aberturas antes do seletor: a folha esta
            # desbalanceada. Dizer "aninhado em regra-arroba" aqui mandaria
            # quem investiga procurar um @media que nao existe.
            raise GuardCannotRun(
                f"chaves desbalanceadas em {arquivo} antes do bloco '{seletor}' "
                f"(sobram {-profundidade_no_seletor} fechamento(s)). Nao consigo "
                "dizer em que escopo o bloco esta, e adivinhar seria aprovar por "
                "silencio.")
        else:
            aninhados += 1

    if len(de_topo) > 1:
        raise GuardCannotRun(
            f"o seletor '{seletor}' abre {len(de_topo)} blocos no nivel de topo de "
            f"{arquivo}. Qual deles vale depende de ordem e especificidade, e "
            "adivinhar seria aprovar por silencio. Deixe um so bloco por tema.")
    if not de_topo:
        if aninhados:
            raise GuardCannotRun(
                f"bloco de tokens '{seletor}' existe em {arquivo} apenas ANINHADO "
                f"dentro de uma regra-arroba (@media/@supports/@layer): {aninhados} "
                "ocorrencia(s). Ele vale so sob a condicao da regra, entao nao serve "
                "como bloco do tema. Nao consigo calcular -- e isso nunca vira "
                "aprovacao.\n"
                f"  declare '{seletor}' no nivel de topo da folha, ou aponte "
                "'seletor_tema_alternativo' para o seletor que de fato aplica.")
        raise GuardCannotRun(f"bloco de tokens '{seletor}' nao encontrado em {arquivo}")

    ini, fim = de_topo[0]
    # A ultima declaracao do bloco pode vir sem `;` -- o CSS permite --, entao
    # o fim do corpo tambem termina uma declaracao. Perde-la fazia o tema
    # alternativo herdar o valor do base no lugar dela, sem aviso.
    return {
        d.group(1): d.group(2).strip()
        for d in re.finditer(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;]+?)\s*(?:;|\Z)",
                             _so_declaracoes_do_seletor(limpo[ini:fim]))
    }


def _so_declaracoes_do_seletor(corpo: str) -> str:
    """
    Do corpo do bloco, guarda so o que aplica AO SELETOR do bloco.

    O bloco e lido inteiro -- inclusive com chaves aninhadas, como a spec
    exige -- mas uma regra aninhada dentro dele (CSS nesting nativo,
    `.dark { --fg: A; .legado { --fg: B } }`) aplica a DESCENDENTES, nao ao
    seletor. Deixar as declaracoes aninhadas entrarem no dicionario fazia a
    ultima vencer: o guard media `B` enquanto a tela mostrava `A`, e um tema
    ilegivel saia LIMPO. O que esta aninhado vira branco; o bloco em si
    continua sendo lido ate a chave que o fecha.
    """
    out, profundidade = [], 0
    for ch in corpo:
        if ch == "{":
            profundidade += 1
            out.append(" ")
            continue
        if ch == "}":
            profundidade = max(0, profundidade - 1)
            out.append(" ")
            continue
        out.append(ch if profundidade == 0 else (" " if ch != "\n" else "\n"))
    return "".join(out)


# ---------------------------------------------------------------------------

@dataclass
class Par:
    frente: str
    fundo: str
    minimo: str
    rotulo: str
    informativo: bool


@dataclass
class Resultado:
    par: Par
    razao_calc: float | None
    exigido: float
    passou: bool
    nota: str


class VerificadorContraste:
    def __init__(self, cfg: dict, pares_path: Path, raiz: Path):
        c = require(cfg, "contraste", "raiz", "tabela")
        self.arquivo = raiz / require(c, "arquivo_estilo", "contraste", "texto")
        self.sel_base = require(c, "seletor_tema_base", "contraste", "texto", nao_vazio=True)
        self.sel_alt = require(c, "seletor_tema_alternativo", "contraste", "texto", nao_vazio=True)
        tabela = load_config(pares_path)
        brutos = tabela.get("par")
        if not brutos:
            raise GuardCannotRun(f"tabela de pares vazia ou ausente em {pares_path}")
        check_type(brutos, "lista de tabelas", "pares", "par")
        self.pares: list[Par] = []
        for i, p in enumerate(brutos):
            faltando = {"frente", "fundo", "minimo", "rotulo"} - set(p)
            if faltando:
                raise GuardCannotRun(f"par #{i + 1} incompleto em {pares_path}: falta {sorted(faltando)}")
            onde = f"par #{i + 1}"
            for chave in ("frente", "fundo", "minimo", "rotulo"):
                check_type(p[chave], "texto", onde, chave)
            # `informativo = "false"` (texto) virava verdadeiro -- texto nao
            # vazio -- e tirava do gate um par que reprova. So booleano vale.
            if "informativo" in p:
                check_type(p["informativo"], "booleano", onde, "informativo")
            if p["minimo"] not in MINIMOS:
                raise GuardCannotRun(
                    f"par #{i + 1}: categoria de minimo desconhecida {p['minimo']!r}; "
                    f"esperava uma de {sorted(MINIMOS)}")
            self.pares.append(Par(p["frente"], p["fundo"], p["minimo"],
                                  p["rotulo"], p.get("informativo", False)))

    def avaliar(self, tokens: dict[str, str], tema: str) -> list[Resultado]:
        out: list[Resultado] = []
        for par in self.pares:
            exigido = MINIMOS[par.minimo]
            ausentes = [t for t in (par.frente, par.fundo) if t not in tokens]
            if ausentes:
                # token ausente REPROVA; nunca passa por omissao
                out.append(Resultado(par, None, exigido, False,
                                     f"TOKEN AUSENTE: {', '.join(ausentes)}"))
                continue
            r = razao(parse_cor(tokens[par.frente], f"{tema} {par.frente}"),
                      parse_cor(tokens[par.fundo], f"{tema} {par.fundo}"))
            out.append(Resultado(par, r, exigido, r >= exigido, ""))
        return out

    def executar(self) -> int:
        if not self.arquivo.is_file():
            raise GuardCannotRun(f"arquivo de estilo ausente: {self.arquivo}")
        css = self.arquivo.read_text(encoding="utf-8")
        base = extrair_bloco(css, self.sel_base, self.arquivo)
        alt_bruto = extrair_bloco(css, self.sel_alt, self.arquivo)
        alt = {**base, **alt_bruto}  # o que o alternativo nao sobrescreve vem do base

        print("GUARD 3 -- contraste computado")
        print(f"arquivo de estilo: {self.arquivo.name}")
        print(f"minimos da norma: texto {MINIMOS['texto']}:1 | "
              f"interface/foco/dica {MINIMOS['interface']}:1")
        print(f"tema alternativo avaliado sobre a UNIAO: {len(alt_bruto)} tokens "
              f"redefinidos, {len(alt) - len(alt_bruto)} herdados do tema base")

        reprovacoes_no_gate = 0
        for tema, tokens in ((f"tema base ({self.sel_base})", base),
                             (f"tema alternativo ({self.sel_alt})", alt)):
            print(f"\n=== {tema} ===")
            resultados = self.avaliar(tokens, tema)
            reprova_gate = sum(1 for r in resultados if not r.passou and not r.par.informativo)
            reprova_info = sum(1 for r in resultados if not r.passou and r.par.informativo)
            n_aval = sum(1 for r in resultados if not r.par.informativo)
            n_info = len(resultados) - n_aval
            for r in sorted(resultados, key=lambda x: (x.par.informativo, x.par.rotulo)):
                calc = f"{r.razao_calc:5.2f}:1" if r.razao_calc is not None else "  ----"
                marca = "[INFORMATIVO] " if r.par.informativo else ""
                if r.par.informativo:
                    veredito = "reprova (nao derruba o gate)" if not r.passou else "passa"
                else:
                    veredito = "PASSA" if r.passou else "REPROVA"
                print(f"  {calc}  min {r.exigido:.1f}:1  {veredito:<28} {marca}{r.par.rotulo}")
                if r.nota:
                    print(f"           ^ {r.nota}")
            print(f"  -- reprovacoes no gate: {reprova_gate} "
                  f"({n_aval} pares avaliados, {n_info} informativos, "
                  f"{reprova_info} deles reprovando)")
            reprovacoes_no_gate += reprova_gate

        if reprovacoes_no_gate:
            print(f"\nTOTAL: {reprovacoes_no_gate} reprovacao(oes) entre os pares avaliados.")
            return EXIT_VIOLATION
        print("\nLIMPO: zero reprovacoes entre os pares avaliados, nos dois temas.")
        return EXIT_CLEAN


def main() -> int:
    ap = argparse.ArgumentParser(description="GUARD 3 -- contraste computado")
    ap.add_argument("--config", default="guards.toml")
    ap.add_argument("--pares", default="pares-contraste.toml")
    args = ap.parse_args()
    cfg_path = Path(args.config).resolve()
    cfg = load_config(cfg_path)
    return VerificadorContraste(cfg, Path(args.pares).resolve(), cfg_path.parent).executar()


if __name__ == "__main__":
    run_guard(main)
