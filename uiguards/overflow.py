"""
GUARD 4 -- Detector de estouro por elemento.

Acha, na pagina RENDERIZADA, os elementos em que o conteudo precisa de mais
largura do que a caixa oferece. Cada resultado e um ELEMENTO: "a pagina
estoura 40px" nao diz o que corrigir; "#tabela-competencias estoura 512px, o
filho responsavel e a linha de competencias" diz.

ESTE GUARD NAO APROVA NEM REPROVA -- ele mede. O veredito pertence ao
consolidador (GUARD 6). Por isso o seu ponto de entrada nunca devolve 1:
    0 -> medi com sucesso (com ou sem defeito encontrado)
    2 -> nao consigo executar (navegador ausente, pagina inacessivel)
Devolver 1 aqui seria confundir "achei defeito" com "reprovei", e o defeito
encontrado e a materia-prima da baseline, nao a sua reprovacao.

A regra de classificacao e a decisao central e esta documentada na propria
sonda (uiguards/overflow_probe.js).

LIMITACOES DECLARADAS -- o que este guard NAO cobre:
  * Mede UM estado da pagina: o que esta montado e assentado no instante da
    leitura. Menu fechado, aba nao aberta, dialogo nao invocado e linha de
    tabela ainda nao carregada nao sao medidos.
  * So o eixo HORIZONTAL. Estouro vertical, sobreposicao, texto cortado na
    vertical e elemento fora da area visivel ficam fora.
  * Nao julga estetica nem usabilidade: um elemento pode caber perfeitamente
    e ainda assim estar ilegivel ou mal alinhado.
  * Nao entra em iframe nem em shadow DOM -- aberto ou fechado: a sonda
    percorre `document.querySelectorAll("*")`, que nao desce em raiz de
    sombra. O hospedeiro e medido como caixa comum; o que esta dentro da
    sombra, nao.
  * O interior de um grafico vetorial nao e medido, por decisao explicita:
    nao sao caixas de layout do CSS, e as larguras que a sonda le nao
    descrevem estouro neles. Um defeito real dentro de um SVG nao e visto.
  * O que o corte esconde e julgado pelo filho que transborda, e ele e
    CONTEUDO (o achado segue contando no placar) se: for, ou contiver renderizado, um
    elemento interativo (link com href, botao, campo de formulario, papel
    ARIA de botao, link ou controle de formulario) ou midia embutida (video,
    iframe, object, embed); OU tiver texto visivel; OU for, ou contiver
    renderizado, imagem ou grafico (img, picture, svg, canvas) sem
    aria-hidden="true" nele ou num ancestral. Fora disso, e decoracao.
    Consequencias: posicao absoluta, pointer-events e aria-hidden NAO tiram
    do placar um filho com texto visivel; grafico ou imagem com aria-hidden
    e sem texto, cortado, sai como decorativo -- inclusive se o autor marcou
    com aria-hidden algo que era informacao. Texto visivel e o no de texto
    nao vazio cujo elemento tem caixa e `visibility: visible`; texto com cor
    igual ao fundo, com opacidade zero ou com tamanho de fonte zero, conta
    como visivel. Tambem conta o texto que o estilo poe por ::before ou
    ::after: os trechos entre aspas do `content` como o navegador o
    serializa, com attr() ja resolvido. counter(), counters(), open-quote e
    close-quote NAO sao lidos: o texto que eles poem na tela nao conta. O que
    vem depois de uma barra fora das aspas e texto alternativo e nao conta;
    espaco, quebra de linha, largura zero, hifen invisivel e marcas de
    direcao tambem nao. Imagem gerada (url(), image-set(), cross-fade(), com
    ou sem prefixo de fornecedor) e glifo de fonte de icone (caractere de
    uso privado) seguem a regra das imagens:
    conteudo, salvo com aria-hidden; gradiente gerado nao conta. O filho e
    julgado inteiro, nao so a parte escondida: o botao que ficou na parte
    visivel tambem o mantem no placar. Elemento so interativo por script ou
    por tabindex (um <div> clicavel sem papel) e imagem de fundo posta pelo
    CSS nao sao vistos: sem texto, contam como decoracao.
  * So os filhos que transbordam sao julgados. O texto do proprio conteiner
    cortado -- no de texto ou ::before do elemento que tem o recorte -- nao
    entra no julgamento: se um filho decorativo tambem transborda, o achado
    sai decorativo mesmo com esse texto cortado. Sem filho que transborde, o
    achado fica no placar.
  * Elemento com `display: contents` nao tem caixa: o texto e o ::before de
    um descendente assim nao contam. `::marker`, o marcador de lista, nao e
    lido.
  * Acima de `limite_por_especie` achados de uma especie na mesma leitura, os
    que sobram (os de menor excedente) saem da lista devolvida. O `placar`
    ainda os conta, e `truncado_por_especie` marca o corte.
  * O piso de severidade descarta estouros pequenos. Um recorte de 1px que
    corta a ultima letra de um rotulo nao aparece.
  * O seletor devolvido e legivel, nao canonico: em pagina muito dinamica ele
    pode nao reencontrar o elemento numa execucao posterior.
  RECURSO COMPLEMENTAR para o que fica descoberto: inspecao visual das capturas
  que a varredura (GUARD 5) grava das rotas com achado.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .common import (
    EXIT_CLEAN, GuardCannotRun, load_config, optional, require, run_guard,
)

SONDA = Path(__file__).with_name("overflow_probe.js")

ORDEM_ESPECIES = [
    "transbordo-visivel",
    "recorte-sem-rolagem",
    "rolagem-nao-declarada",
    "recorte-decorativo",
]
DESCRICAO_ESPECIE = {
    "transbordo-visivel": "o excedente fica a mostra, fora da caixa",
    "recorte-sem-rolagem": "o corte esconde conteudo e NAO ha rolagem ate ele",
    "recorte-decorativo": "o corte so esconde enfeite (FORA DO PLACAR)",
    "rolagem-nao-declarada": "ha rolagem horizontal que ninguem declarou",
}


def config_de_medicao(cfg: dict) -> tuple[float, int, dict]:
    """Piso, limite e ancoras de [medicao], com o tipo conferido (errado e 2)."""
    med = require(cfg, "medicao", "raiz", "tabela")
    piso = require(med, "piso_severidade_px", "medicao", "numero")
    limite = require(med, "limite_por_especie", "medicao", "inteiro")
    if piso < 0:
        raise GuardCannotRun(f"piso_severidade_px negativo em [medicao]: {piso}")
    if limite < 1:
        raise GuardCannotRun(f"limite_por_especie precisa ser ao menos 1 em [medicao]: {limite}")
    ancoras = optional(med, "ancoras", "medicao", "tabela de textos", {})
    return float(piso), limite, ancoras


def carregar_sonda() -> str:
    if not SONDA.is_file():
        raise GuardCannotRun(f"sonda ausente: {SONDA}")
    return SONDA.read_text(encoding="utf-8")


def assentar(page) -> None:
    """
    Imagens ja anexadas decodificadas e fontes prontas.

    Qualquer uma das duas pode ficar pronta depois que o documento carregou,
    e com isso mexer nas larguras. A funcao espera por cada uma delas, e nao
    por um numero fixo de milissegundos.
    """
    page.wait_for_load_state("domcontentloaded")
    page.evaluate(
        """async () => {
            const imgs = [...document.images].filter(i => !i.complete);
            await Promise.all(imgs.map(i => i.decode().catch(() => {})));
            if (document.fonts && document.fonts.ready) await document.fonts.ready;
        }"""
    )


def medir(page, piso: float, limite: int, ancoras: dict | None = None) -> dict:
    """Uma leitura da sonda. Quem chama ja esperou a pagina carregar (ver `assentar`)."""
    try:
        return page.evaluate(carregar_sonda(),
                             {"piso": piso, "limite": limite, "ancoras": ancoras or {}})
    except Exception as exc:  # noqa: BLE001
        raise GuardCannotRun(f"a sonda nao executou na pagina: {exc}") from exc


def conjunto_do_placar(leitura: dict) -> set[tuple[str, str]]:
    """
    O que identifica uma leitura para a estabilizacao: o CONJUNTO de
    (especie, seletor) do placar.

    Duas leituras seguidas sao comparadas por esse conjunto, e nao pelos
    excedentes em pixels: o mesmo defeito pode medir 512.0 numa leitura e
    512.5 na seguinte, e uma comparacao por valor nunca daria as duas por
    iguais.
    """
    return {
        (a["especie"], a["seletor"])
        for nome in ORDEM_ESPECIES
        for a in leitura["especies"].get(nome, [])
        if a["no_placar"]
    }


def formatar(leitura: dict, cabecalho: str = "") -> str:
    m = leitura["metricas"]
    linhas = [f"GUARD 4 -- estouro por elemento {cabecalho}".rstrip()]
    linhas.append(
        f"  viewport {m['viewport_largura']}x{m['viewport_altura']} | "
        f"documento {m['documento_conteudo']}/{m['documento_visivel']} "
        f"(excedente da pagina {m['excedente_da_pagina']}) | "
        f"{m['elementos_examinados']} elementos examinados")
    linhas.append(
        f"  piso de severidade {leitura['piso_aplicado']}px | "
        f"placar {leitura['placar']} | fora do placar {leitura['fora_do_placar']} "
        f"(decorativos {leitura['decorativos']}) | "
        f"abaixo do piso {leitura['abaixo_do_piso']} | "
        f"isentos {leitura['ignorados_por_isencao']}")
    for nome in ORDEM_ESPECIES:
        grupo = leitura["especies"].get(nome, [])
        if not grupo:
            continue
        linhas.append(f"\n  [{nome}] {DESCRICAO_ESPECIE[nome]} -- {len(grupo)}")
        if leitura["truncado_por_especie"].get(nome):
            linhas.append("    (lista truncada pelo limite por especie)")
        for a in grupo:
            marca = " (ha achado mais interno)" if a["tem_achado_mais_interno"] else ""
            linhas.append(
                f"    {a['seletor']}  conteudo {a['largura_conteudo']} / "
                f"visivel {a['largura_visivel']} = excedente {a['excedente']}px{marca}")
            if a["filho_responsavel"]:
                linhas.append(f"      filho responsavel: {a['filho_responsavel']}")
    return "\n".join(linhas)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="GUARD 4 -- medicao avulsa de estouro por elemento numa URL")
    ap.add_argument("--config", default="guards.toml")
    ap.add_argument("--url", required=True)
    ap.add_argument("--largura", type=int, default=390)
    ap.add_argument("--altura", type=int, default=844)
    ap.add_argument("--json", action="store_true", help="saida em JSON")
    args = ap.parse_args()

    cfg = load_config(Path(args.config).resolve())
    piso, limite, ancoras = config_de_medicao(cfg)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise GuardCannotRun(f"playwright nao instalado: {exc}") from exc

    with sync_playwright() as pw:
        try:
            navegador = pw.chromium.launch()
        except Exception as exc:  # noqa: BLE001
            raise GuardCannotRun(f"nao consigo abrir o navegador: {exc}") from exc
        ctx = navegador.new_context(
            viewport={"width": args.largura, "height": args.altura},
            reduced_motion="reduce")
        page = ctx.new_page()
        try:
            page.goto(args.url, wait_until="domcontentloaded")
        except Exception as exc:  # noqa: BLE001
            raise GuardCannotRun(f"nao consigo carregar {args.url}: {exc}") from exc
        assentar(page)
        leitura = medir(page, piso, limite, ancoras)
        navegador.close()

    print(json.dumps(leitura, indent=2, ensure_ascii=False, sort_keys=True)
          if args.json else formatar(leitura, f"-- {args.url}"))
    return EXIT_CLEAN  # o detector mede; quem da veredito e o GUARD 6


if __name__ == "__main__":
    run_guard(main)
