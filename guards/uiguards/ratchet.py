"""
GUARD 2 -- Layout responsivo (catraca).

Deixa a divida de layout que o projeto ja tem ser paga aos poucos, sem
permitir que ela AUMENTE. Um gate de zero absoluto, ligado enquanto ha
divida, reprovaria qualquer commit ate a ultima violacao sair. A catraca
aceita a divida que ja existe, recusa a nova e vai apertando.

Quatro causas de estouro horizontal, uma regra para cada:
  R1 tabela sem contencao de rolagem
  R2 largura fixa em pixels como valor arbitrario
  R3 impedimento de quebra de linha em celula de conteudo variavel
  R4 truncamento sem exposicao do valor integro

CODIGOS DE SAIDA: 0 limpo | 1 achei violacao | 2 nao consigo executar.
Baseline ausente ou malformada e 2, nunca 1: nao consigo executar. Conta
como malformada a chave que nao tem a forma `arquivo::regra` com uma das
quatro regras -- o ultimo `::` separa a regra, entao o nome do arquivo pode
conter `::` --, e a contagem que nao e inteiro maior ou igual a zero,
booleano e numero fracionario incluidos.

LIMITACOES DECLARADAS -- o que este guard NAO cobre:
  * Leitura lexica do fonte, sem arvore sintatica: nenhuma das quatro regras
    ve classe que so se forma em tempo de execucao. Dentro de
    `className={...}` os LITERAIS contam (e o que torna
    `cn("overflow-x-auto", ...)` visivel como contencao); o que vem de
    variavel, de concatenacao ou de outro modulo, nao.
  * Regra 1: os ancestrais da tabela sao achados subindo pelas linhas de
    indentacao menor. Indentacao irregular engana a busca. De cada ancestral
    so e lida a linha em que a indentacao cai: quando os atributos dele
    ocupam varias linhas e a classe de rolagem fica numa linha abaixo da do
    `<` (formatacao comum), a rolagem nao e vista e a tabela contida e
    acusada. Quando a rolagem vem de um componente escrito em OUTRO arquivo,
    esta leitura nao a ve; por isso o componente-padrao de tabela e aceito
    pelo nome, sem que a classe de rolagem precise aparecer. So conta como
    contencao a rolagem declarada em atributo class/className de linha de
    codigo: comentario e string nao contem coisa nenhuma.
  * A regra 3 so olha celulas de tabela; texto de tamanho imprevisivel em
    card, lista ou qualquer outro elemento fica de fora. Mesmo na tabela, so
    a tag `<td>` escrita como tal e examinada, e so pela classe dela:
    `whitespace-nowrap` num filho da celula, a classe `text-nowrap` e a
    celula escrita como componente (`<TableCell>`) passam. Alem disso exige
    casamento POSITIVO com a lista de
    colunas de conteudo variavel: celula cujo campo nao esta nessa lista nao
    e classificada e passa -- inclusive celula so de coluna atomica. Celula
    MISTA (conteudo variavel mais coluna atomica) e acusada: quebra pelo
    lado variavel. O casamento e por palavra em todo o corpo da celula, texto
    fixo incluido: um rotulo literal `Nome:` numa celula so de identificador a
    classifica como variavel. Os nomes de coluna vem de lista mantida a mao e
    nada avisa quando ela envelhece.
  * A regra 2 so reconhece a forma `w-[Npx]`. Largura em pixels por estilo em
    linha (`style={{ width: 300 }}`), por `basis-[..]`, `flex-[..]` ou
    `grid-cols-[..]`, ou largura fixa noutra unidade (`w-[20rem]`), passa.
  * A regra 4 procura o atributo acessivel so na abertura da tag que declara
    o truncamento, em qualquer linha dela, ignorando comentario e conteudo de
    string -- texto morto nao expoe valor -- e exigindo a FORMA de atributo
    (nome colado ao `=`, valor entre aspas ou chaves) com valor nao vazio
    (`title=""` e `title={""}` nao isentam). O valor nao e julgado alem
    disso: `title=" -"` ou `title={x}` com `x` vazio em runtime isentam. A abertura e lida
    inteira, expressoes incluidas: uma atribuicao escrita sem espaco dentro
    de uma delas (`onClick={() => { title="x" }}`) se passaria por atributo.
    Atributo que expoe o valor em OUTRO elemento -- o pai, um filho, um
    rotulo associado -- nao conta, e o truncamento e acusado. Classe de
    truncamento fora da abertura de uma tag (guardada em variavel e aplicada
    adiante) nao tem tag onde procurar o atributo e e sempre acusada.
    Truncamento e `truncate`, `text-ellipsis` e `line-clamp-N`; a busca e
    pela palavra em qualquer ponto do codigo fora de comentario, entao uma
    funcao chamada `truncate(...)` tambem aciona a regra.
  * NADA e medido com a pagina rodando. Se algo estoura de fato e pergunta
    para a medicao em navegador (GUARDS 4-6), nao para esta leitura.
  * `--modo refixar` grava a contagem atual como esta, MAIOR que a anterior
    inclusive: o guard nao sabe se quem roda pagou divida ou so quer calar a
    catraca. Ele imprime as chaves que CRESCERAM, e so isso; nao recusa. A
    catraca, portanto, segura enquanto alguem revisa o diff da baseline no
    commit que a re-fixou.
  * O marcador de excecao vale para a propria linha e, quando esta sozinho
    na linha, para a seguinte (ver `uiguards/common.py`).
  * A catraca conta por arquivo e por regra e deixa a linha de fora de
    proposito: mover codigo dentro do arquivo nao pode acusar divida nova. O
    preco e que, dentro do mesmo par arquivo/regra, uma violacao nova que
    ocupa o lugar de uma corrigida deixa a contagem igual e passa.
  RECURSO COMPLEMENTAR para o que fica descoberto: a varredura multi-viewport
  (GUARD 5), que mede a largura real na pagina renderizada.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

from .common import (
    EXIT_CLEAN, EXIT_VIOLATION, GuardCannotRun, ScannedSource,
    enclosing_element, escaped_at, iter_source_files, load_config, optional,
    parse_tag, rel, require, run_guard, scan_source,
)

RAIZ_KIT = Path(__file__).resolve().parent.parent

GUARD_ID = "responsivo"

REGRAS = {
    "R1-tabela-sem-rolagem": (
        "Tabela sem contencao de rolagem horizontal",
        "envolver no componente-padrao de tabela, ou num ancestral com overflow-x-auto",
    ),
    "R2-largura-fixa-px": (
        "Largura fixa em pixels (valor arbitrario)",
        "usar largura fluida (w-full, flex-1) ou limite com max-w-[..] / min-w-[..]",
    ),
    "R3-nowrap-conteudo-variavel": (
        "Quebra de linha impedida em celula de conteudo variavel",
        "remover whitespace-nowrap da celula; ele so cabe onde o conteudo tem tamanho limitado",
    ),
    "R4-truncamento-sem-valor": (
        "Truncamento sem expor o valor integro",
        "acrescentar title= ou aria-label= com o valor completo na mesma tag",
    ),
}
ORDEM_REGRAS = list(REGRAS)

ROLAGEM_H = ("overflow-x-auto", "overflow-x-scroll", "overflow-auto", "overflow-scroll")
# Truncamento da regra 4: corte em uma linha (`truncate`, `text-ellipsis`) e
# corte em N linhas (`line-clamp-N`, `line-clamp-[..]`). `line-clamp-none`
# desfaz o corte e nao entra.
TRUNCAMENTO = re.compile(
    r"(?<![-\w])(truncate|text-ellipsis|line-clamp-(?:\d+|\[[^\]\s]+\]))(?![-\w])")


@dataclass(frozen=True)
class Achado:
    regra: str
    arquivo: str
    linha: int
    trecho: str
    detalhe: str

    @property
    def chave(self) -> str:
        """Onde a catraca soma este achado: arquivo e regra; a linha fica de fora."""
        return f"{self.arquivo}::{self.regra}"

    def ordem(self):
        return (ORDEM_REGRAS.index(self.regra), self.arquivo, self.linha, self.trecho)


def _expressao_de_classe(texto: str, abre: int) -> str:
    """Conteudo de `className={...}` a partir da chave, ate o fechamento."""
    profundidade, i, n = 0, abre, len(texto)
    while i < n:
        if texto[i] == "{":
            profundidade += 1
        elif texto[i] == "}":
            profundidade -= 1
            if profundidade == 0:
                return texto[abre + 1 : i]
        i += 1
    return texto[abre + 1 :]


def _literais_de_expressao(trecho: str) -> list[str]:
    """
    Tokens de classe dos LITERAIS de uma expressao de classe.

    Em `className={cn("overflow-x-auto", ativo && "p-2")}` a classe esta num
    literal dentro da expressao; o resto e codigo e nao declara classe. Aceitar
    so aspas logo depois do `=` fazia esta forma -- a mais comum em projeto que
    usa utilitario de composicao -- deixar de contar, e entao a tabela CONTIDA
    virava acusacao.
    """
    out: list[str] = []
    for m in re.finditer(r"[\"'`]([^\"'`]*)[\"'`]", trecho):
        out.extend(m.group(1).split())
    return out


def classes_da_tag(texto: str, lt: int, gt: int) -> list[str]:
    corpo = texto[lt:gt]
    out: list[str] = []
    for m in re.finditer(r"class(?:Name)?\s*=\s*([\"'`])(.*?)\1", corpo, re.S):
        out.extend(m.group(2).split())
    for m in re.finditer(r"class(?:Name)?\s*=\s*\{", corpo):
        out.extend(_literais_de_expressao(_expressao_de_classe(corpo, m.end() - 1)))
    return out


def classes_da_linha(linha: str) -> set[str]:
    """
    Tokens de classe declarados NESTA linha, como classe de verdade.

    Procurar a palavra por substring na linha crua aceitava como contencao
    tanto um comentario que apenas MENCIONA `overflow-x-auto` quanto uma
    string qualquer que contenha o texto. Comentario nao e avaliado, e uma
    string tambem nao declara classe nenhuma: so vale o que esta dentro de um
    atributo `class`/`className` -- em aspas diretas ou em literal dentro da
    expressao entre chaves.
    """
    out: set[str] = set()
    for m in re.finditer(r"class(?:Name)?\s*=\s*[\"'`]([^\"'`]*)", linha):
        out.update(m.group(1).split())
    for m in re.finditer(r"class(?:Name)?\s*=\s*\{", linha):
        out.update(_literais_de_expressao(_expressao_de_classe(linha, m.end() - 1)))
    return out


def _valor_nao_vazio(texto: str, abre: int) -> bool:
    """
    O valor de atributo que comeca em `abre` (aspa ou chave) tem conteudo?

    `title=""`, `title={}` e `title={""}` nao expoem valor nenhum.
    """
    q = texto[abre]
    if q == "{":
        corpo = _expressao_de_classe(texto, abre).strip()
        return bool(corpo) and not re.fullmatch(r"([\"'`])\s*\1", corpo)
    fim = texto.find(q, abre + 1)
    return fim > abre and bool(texto[abre + 1 : fim].strip())


def _sem_conteudo_de_literal(src: ScannedSource) -> str:
    """Texto mascarado com o CONTEUDO dos literais tambem apagado.

    Guarda as posicoes das linhas: o que some vira branco, nunca desaparece.
    """
    buf = list(src.masked)
    for lit in src.literals:
        for k in range(lit.start, min(lit.end, len(buf))):
            if buf[k] != "\n":
                buf[k] = " "
    return "".join(buf)


class VerificadorResponsivo:
    def __init__(self, cfg: dict, raiz_projeto: Path, cfg_path: Path | None = None):
        r = require(cfg, "responsivo", "raiz", "tabela")
        proj = require(cfg, "projeto", "raiz", "tabela")
        self.raiz_projeto = raiz_projeto
        self.raiz_ui = (raiz_projeto / require(proj, "raiz_ui", "projeto", "texto")).resolve()
        self.extensoes = require(proj, "extensoes", "projeto", "lista de textos", nao_vazio=True)
        self.ignorar = optional(proj, "ignorar_dirs", "projeto", "lista de textos", [])
        self.baseline_path = raiz_projeto / require(r, "baseline", "responsivo", "texto")
        self.comp_tabela = require(r, "componente_tabela", "responsivo", "texto")
        self.arq_comp_tabela = require(r, "arquivo_componente_tabela", "responsivo", "texto")
        self.col_variavel = [c.lower() for c in require(
            r, "colunas_conteudo_variavel", "responsivo", "lista de textos")]
        self.col_atomica = [c.lower() for c in require(
            r, "colunas_atomicas", "responsivo", "lista de textos")]
        self.cfg_path = cfg_path or (raiz_projeto / "guards.toml")
        self.achados: list[Achado] = []
        self.arquivos_varridos = 0

    # -- regras -------------------------------------------------------------
    def _r1_tabelas(self, src: ScannedSource, arquivo: str, chave_ui: str):
        if chave_ui == self.arq_comp_tabela:
            return  # o arquivo que DEFINE o componente-padrao e isento
        m = src.masked
        for match in re.finditer(r"<table\b", m):
            linha = src.line_of(match.start())
            if escaped_at(src, linha, GUARD_ID):
                continue
            if self._tem_contencao(src, linha):
                continue
            self.achados.append(Achado(
                "R1-tabela-sem-rolagem", arquivo, linha, src.snippet(match.start()),
                f"sem ancestral com rolagem horizontal e fora de <{self.comp_tabela}>"))

    def _tem_contencao(self, src: ScannedSource, linha: int) -> bool:
        """
        Procura contencao entre os ancestrais, achados pela indentacao (ver
        DECISOES.md 1.1).

        Sobe procurando linhas com indentacao estritamente menor que a da
        tabela; a primeira que abrir tag e candidata a ancestral.

        A subida corre sobre o texto MASCARADO, nao sobre a linha crua:
        comentario nao e avaliado (a spec e explicita), e linha que so tem
        comentario vira branco e sai do caminho. A rolagem so conta como
        contencao se for CLASSE declarada -- mencao em comentario ou texto
        solto dentro de uma string nao contem coisa nenhuma.
        """
        linhas = src.masked.split("\n")
        alvo = linhas[linha - 1]
        ind_corrente = len(alvo) - len(alvo.lstrip())
        for i in range(linha - 2, -1, -1):
            bruta = linhas[i]
            if not bruta.strip():
                continue
            ind = len(bruta) - len(bruta.lstrip())
            if ind >= ind_corrente:
                continue
            ind_corrente = ind
            # componente-padrao de tabela reconhecido pelo nome
            if re.search(r"<" + re.escape(self.comp_tabela) + r"\b", bruta):
                return True
            if classes_da_linha(bruta) & set(ROLAGEM_H):
                return True
            if ind == 0:
                break
        return False

    def _r2_largura_fixa(self, src: ScannedSource, arquivo: str):
        # `max-w-[..]` e `min-w-[..]` NAO contam: teto e piso deixam a largura
        # se ajustar; so a largura cravada impede.
        padrao = re.compile(r"(?<![-\w])w-\[(\d+(?:\.\d+)?)px\]")
        for match in padrao.finditer(src.masked):
            linha = src.line_of(match.start())
            if escaped_at(src, linha, GUARD_ID):
                continue
            self.achados.append(Achado(
                "R2-largura-fixa-px", arquivo, linha, match.group(0),
                f"largura cravada em {match.group(1)}px"))

    def _r3_nowrap(self, src: ScannedSource, arquivo: str):
        m = src.masked
        for match in re.finditer(r"<td\b", m):
            parsed = parse_tag(m, match.start())
            if not parsed:
                continue
            nome, gt, autofechada = parsed
            if "whitespace-nowrap" not in classes_da_tag(m, match.start(), gt):
                continue
            linha = src.line_of(match.start())
            if escaped_at(src, linha, GUARD_ID):
                continue
            fim = m.find("</td>", gt)
            corpo = m[gt : fim if fim > 0 else gt + 200].lower()
            campos = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", corpo)
            # O casamento com conteudo VARIAVEL manda. Deixar a lista atomica
            # curto-circuitar antes isentava a celula mista -- nome mais
            # estado, endereco mais codigo -- que e comum em tabela real e
            # quebra pelo lado do conteudo variavel, nao pelo atomico.
            # Celula so-atomica nao casa nenhum variavel e passa por aqui.
            variaveis = [c for c in campos if c in self.col_variavel]
            if not variaveis:
                continue  # coluna atomica ou nao classificada: ver limitacoes
            atomicas = [c for c in campos if c in self.col_atomica]
            mista = (f"; a celula tambem cita coluna atomica ({atomicas[0]}), "
                     "e mesmo assim quebra pelo conteudo variavel" if atomicas else "")
            self.achados.append(Achado(
                "R3-nowrap-conteudo-variavel", arquivo, linha, src.snippet(match.start()),
                f"celula de conteudo variavel ({variaveis[0]}) com "
                f"whitespace-nowrap{mista}"))

    def _r4_truncamento(self, src: ScannedSource, arquivo: str):
        m = src.masked
        # Atributo procurado sobre o texto mascarado E SEM O CONTEUDO DOS
        # LITERAIS: nem um comentario que mencione `title=` nem uma string que
        # contenha esse texto expoem valor nenhum. O nome do atributo vive
        # fora das aspas, entao `title="Endereco completo"` continua valendo;
        # `const dica = "falta title= aqui"` deixa de valer. As posicoes sao
        # as mesmas nos dois textos.
        sem_literais = _sem_conteudo_de_literal(src)
        for match in re.finditer(TRUNCAMENTO, m):
            linha = src.line_of(match.start())
            if escaped_at(src, linha, GUARD_ID):
                continue
            # O atributo so vale na MESMA tag do truncamento, em qualquer
            # linha dela -- a mesma leitura de tag inteira da regra 3. Uma
            # janela de linhas ao redor deixava o title= de um elemento
            # vizinho isentar o truncamento, e acusava o title= da propria
            # tag quando ele caia longe.
            ctx = enclosing_element(m, match.start())
            if ctx is None:
                detalhe = "fora da abertura de uma tag: nao ha tag onde procurar title= ou aria-label="
            else:
                lt, nome, gt, _autofechada = ctx
                # Forma de ATRIBUTO: nome colado ao `=`, com valor entre aspas
                # ou chaves. `const title = "Clientes"` nao expoe valor nenhum.
                # O valor tem de existir: `title=""` casa a forma e nao expoe
                # nada. Os literais estao em branco em `sem_literais`, entao o
                # valor e lido no texto mascarado, na mesma posicao.
                if any(_valor_nao_vazio(m, lt + a.end() - 1) for a in re.finditer(
                        r"(?<![\w$.\-])(?:title|aria-label)=\s*[{\"'`]",
                        sem_literais[lt : gt + 1])):
                    continue
                detalhe = (f"sem title= nem aria-label= com valor na propria tag <{nome}> "
                           "(atributo vazio nao expoe nada)")
            self.achados.append(Achado(
                "R4-truncamento-sem-valor", arquivo, linha, src.snippet(match.start()),
                f"'{match.group(1)}' {detalhe}"))

    # -- execucao -----------------------------------------------------------
    def coletar(self):
        arquivos = iter_source_files(self.raiz_ui, self.extensoes, self.ignorar)
        if not arquivos:
            raise GuardCannotRun(
                f"nenhum arquivo com extensoes {self.extensoes} sob {self.raiz_ui}")
        for path in arquivos:
            arquivo = rel(path, self.raiz_projeto)
            chave_ui = rel(path, self.raiz_ui)
            try:
                texto = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                raise GuardCannotRun(f"nao consigo ler {arquivo}: {exc}") from exc
            self.arquivos_varridos += 1
            src = scan_source(texto)
            self._r1_tabelas(src, arquivo, chave_ui)
            self._r2_largura_fixa(src, arquivo)
            self._r3_nowrap(src, arquivo)
            self._r4_truncamento(src, arquivo)
        self.achados.sort(key=Achado.ordem)

    def contagem(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for a in self.achados:
            out[a.chave] = out.get(a.chave, 0) + 1
        return dict(sorted(out.items()))

    def comando_refixar(self) -> str:
        """O comando que re-fixa, valido de qualquer diretorio (caminhos absolutos)."""
        return (f"cd {RAIZ_KIT} && python3 -m uiguards.ratchet "
                f"--config {self.cfg_path} --modo refixar")

    def ler_baseline(self) -> dict[str, int]:
        if not self.baseline_path.is_file():
            raise GuardCannotRun(
                f"baseline ausente: {self.baseline_path}\n"
                f"  para criar: {self.comando_refixar()}")
        try:
            bruto = self.baseline_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise GuardCannotRun(f"baseline ilegivel em {self.baseline_path}: {exc}") from exc
        try:
            dados = json.loads(bruto)
        except json.JSONDecodeError as exc:
            raise GuardCannotRun(f"baseline malformada em {self.baseline_path}: {exc}") from exc
        if not isinstance(dados, dict):
            raise GuardCannotRun(
                f"baseline malformada em {self.baseline_path}: esperava um objeto JSON")
        chaves = dados.get("chaves")
        if not isinstance(chaves, dict):
            raise GuardCannotRun(
                f"baseline malformada em {self.baseline_path}: esperava objeto 'chaves'")
        for chave, contagem in chaves.items():
            # a regra nunca contem '::'; o nome do arquivo pode conter
            arquivo, separador, regra = chave.rpartition("::")
            if not separador or not arquivo or regra not in REGRAS:
                raise GuardCannotRun(
                    f"baseline malformada em {self.baseline_path}: a chave {chave!r} nao "
                    f"tem a forma 'arquivo::regra' com uma regra conhecida "
                    f"({', '.join(REGRAS)})")
            # bool e subclasse de int em Python: `true` passaria por contagem 1
            if isinstance(contagem, bool) or not isinstance(contagem, int) or contagem < 0:
                raise GuardCannotRun(
                    f"baseline malformada em {self.baseline_path}: a contagem de {chave!r} "
                    f"tem de ser um inteiro maior ou igual a zero, veio {contagem!r}")
        return chaves

    def escrever_baseline(self, contagem: dict[str, int]):
        payload = {
            "descricao": "Contagem conhecida de violacoes, por arquivo e regra. "
                         "A linha nao entra: mover codigo nao conta como divida nova.",
            "total": sum(contagem.values()),
            "chaves": dict(sorted(contagem.items())),
        }
        self.baseline_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
            encoding="utf-8")

    def _listar(self, achados: list[Achado], titulo: str):
        por_regra: dict[str, list[Achado]] = {}
        for a in achados:
            por_regra.setdefault(a.regra, []).append(a)
        for regra in ORDEM_REGRAS:
            grupo = por_regra.get(regra)
            if not grupo:
                continue
            nome, dica = REGRAS[regra]
            print(f"\n[{regra}] {nome} -- {len(grupo)} ocorrencia(s) {titulo}")
            print(f"  correcao: {dica}")
            for a in grupo:
                print(f"    {a.arquivo}:{a.linha}: {a.trecho}")
                print(f"      ^ {a.detalhe}")
        print(f"\n  excecao legitima se declarada: comentario "
              f"'ui-guard-allow({GUARD_ID}): <motivo>' na linha ou na anterior")

    def executar(self, modo: str) -> int:
        self.coletar()
        atual = self.contagem()
        total_atual = sum(atual.values())

        if modo == "refixar":
            # A re-fixacao grava o que medir, inclusive divida MAIOR que a
            # anterior: o guard nao sabe se quem roda pagou divida ou so quer
            # silenciar a catraca. O que ele faz e nomear as chaves que
            # CRESCERAM, para que isso fique a vista de quem revisa o diff da
            # baseline. A mensagem nao muda o que e gravado.
            try:
                anterior = self.ler_baseline()
            except GuardCannotRun:
                anterior = None
            self.escrever_baseline(atual)
            print("GUARD 2 -- layout responsivo (catraca)")
            print(f"baseline RE-FIXADA em {rel(self.baseline_path, self.raiz_projeto)}")
            print(f"  chaves: {len(atual)}   total de violacoes conhecidas: {total_atual}")
            print("  so este comando grava a baseline; rodando como gate, o guard "
                  "nunca a altera.")
            if anterior is None:
                print("  (nao havia baseline legivel antes: nada a comparar)")
            else:
                cresceram = {k: (anterior.get(k, 0), v) for k, v in atual.items()
                             if v > anterior.get(k, 0)}
                if cresceram:
                    print("\n>>> AVISO: esta re-fixacao ACEITOU divida MAIOR que a anterior."
                          " Chaves que CRESCERAM:")
                    for k in sorted(cresceram):
                        b, n = cresceram[k]
                        print(f"    {k}: conhecida {b} -> gravada {n}")
                    print("    Re-fixar existe para quem REDUZIU a divida. Confira o diff "
                          "da baseline antes do commit.")
            return EXIT_CLEAN

        if modo == "estrito":
            print("GUARD 2 -- layout responsivo (modo ESTRITO: nenhuma violacao e aceita)")
            print(f"arquivos varridos: {self.arquivos_varridos}")
            if not self.achados:
                print("\nLIMPO: 0 violacoes de layout.")
                return EXIT_CLEAN
            self._listar(self.achados, "")
            print(f"\nTOTAL: {total_atual} violacoes. O modo estrito nao aceita nenhuma.")
            return EXIT_VIOLATION

        # ---- modo catraca ----
        base = self.ler_baseline()
        total_base = sum(base.values())
        cresceram = {k: (base.get(k, 0), v) for k, v in atual.items() if v > base.get(k, 0)}
        reduziram = {k: (base[k], atual.get(k, 0)) for k in base if atual.get(k, 0) < base[k]}

        print("GUARD 2 -- layout responsivo (catraca)")
        print(f"arquivos varridos: {self.arquivos_varridos}")
        print(f"contagem conhecida: {total_base}   contagem atual: {total_atual}   "
              f"novas: {sum(n - b for b, n in cresceram.values())}")

        codigo = EXIT_CLEAN
        if cresceram:
            codigo = EXIT_VIOLATION
            chaves = set(cresceram)
            novos = [a for a in self.achados if a.chave in chaves]
            print("\n>>> A DIVIDA CRESCEU. Chaves acima do teto conhecido:")
            for k in sorted(cresceram):
                b, n = cresceram[k]
                print(f"    {k}: conhecida {b} -> atual {n}")
            self._listar(novos, "(chave que cresceu)")

        if reduziram:
            codigo = EXIT_VIOLATION
            print("\n>>> A DIVIDA CAIU E A BASELINE NAO FOI RE-FIXADA.")
            print("    Se a baseline nao descer neste mesmo commit, a folga aberta pode")
            print("    ser ocupada de novo mais tarde sem que nada acuse. Chaves reduzidas:")
            for k in sorted(reduziram):
                b, n = reduziram[k]
                print(f"    {k}: conhecida {b} -> atual {n}")
            print("\n    RE-FIXE NO MESMO COMMIT:")
            print(f"      {self.comando_refixar()}")

        if codigo == EXIT_CLEAN:
            print("\nLIMPO: nenhuma violacao nova e nenhuma chave reduzida sem re-fixacao.")
        return codigo


def main() -> int:
    ap = argparse.ArgumentParser(description="GUARD 2 -- layout responsivo (catraca)")
    ap.add_argument("--config", default="guards.toml")
    ap.add_argument("--modo", choices=("catraca", "estrito", "refixar"), default="catraca")
    args = ap.parse_args()
    cfg_path = Path(args.config).resolve()
    cfg = load_config(cfg_path)
    return VerificadorResponsivo(cfg, cfg_path.parent, cfg_path).executar(args.modo)


if __name__ == "__main__":
    run_guard(main)
