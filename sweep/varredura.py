"""
GUARD 5 -- Varredura multi-viewport como especificacao executavel.

Faz da medicao do GUARD 4 um teste que fica no projeto e pode servir de
gate, e cuida para que a baseline gravada saia IGUAL quando nada mudou.

CADA VIEWPORT E UM TESTE PROPRIO e grava o seu parcial ao terminar: se um
viewport for interrompido (tempo limite, erro), os que ja terminaram
continuam no disco. Juntar os parciais e trabalho do GUARD 6, em etapa
separada.

A varredura NAO FALHA por encontrar defeitos -- encontra-los e a funcao dela.
Ela falha quando:
  * uma rota termina num endereco diferente do pedido;
  * resolve menos paginas de detalhe do que o minimo declarado;
  * o estado inicial nao foi aplicado.
Matriz de rotas invalida -- tipo errado, chave ausente, nenhum viewport,
nenhuma area, area sem rota -- e recusada antes de medir (2 por
`sweep/executar.py`): medir nada nao e base limpa.

ROTA NAO MEDIVEL: quando a resposta principal da navegacao ate a propria
rota tem status HTTP 4xx ou 5xx (ou o navegador nao entrega resposta
principal), a pagina que chega nao e medida. O registro da rota sai com
`nao_medivel` e o motivo, sem achados, e o GUARD 6 o conta como rota
quebrada. A decisao e SO pelo status da resposta; o conteudo da pagina nao
entra.

SAIDA: `--saida` de `sweep/executar.py` (ou VARREDURA_SAIDA). Sem ela, o
padrao e `out/medicao`, e nunca `out/varredura`, que guarda a baseline
fixada: medir de novo nao a sobrescreve.

LIMITACOES DECLARADAS -- o que este guard NAO cobre:
  * Herda TODAS as limitacoes do GUARD 4 (mede um estado, so o eixo
    horizontal, nao entra em iframe nem em SVG).
  * Mede a rota como ela abre. Nao clica, nao preenche, nao abre dialogo, nao
    pagina lista: fluxo com varias etapas nao e coberto.
  * Um unico navegador (Chromium). Diferenca de motor -- metrica de fonte,
    largura de barra de rolagem -- nao e vista.
  * O destino e conferido uma vez, logo depois da navegacao. Um
    redirecionamento que a propria pagina faz mais tarde (por script, com
    atraso) nao e conferido de novo, e a medicao seguinte sai com o nome da
    rota pedida.
  * Viewports discretos: um defeito que so aparece entre duas larguras
    medidas passa.
  * Uma leitura e aceita assim que o placar dela repete o da leitura
    anterior. Oscilacao mais lenta que o intervalo entre duas leituras
    produz essa repeticao e escapa como estavel.
  * O registro grava so a lista que a sonda devolveu, ja cortada pelo limite
    por especie, e nao copia `truncado_por_especie`. O que passou do limite
    fica fora da estabilizacao e da assinatura, e nada no parcial marca o
    corte alem da diferenca entre `placar` e os achados do registro.
  * Depende de dados vivos: uma rota cujo conteudo mudou pode mudar o placar
    sem que o codigo tenha mudado.
  * Uma pagina de erro entregue com status de SUCESSO (200, por exemplo) e
    medida em nome da rota pedida: a decisao de "nao medivel" olha so
    o status da resposta principal, nunca o texto da tela. Sem estouro, ela
    conta como rota saudavel. Um redirecionamento, que termina noutro
    endereco, continua sendo falha de destino, nao rota nao medivel.
  * A barreira "nenhuma baseline sem detector provado" vive no ponto de
    entrada da suite (`sweep/executar.py`), nao neste modulo. Rodar este
    modulo direto (`python3 -m unittest sweep.varredura`) grava parciais sem
    ter rodado a prova do detector, e nada no parcial registra a diferenca.
    Nao ha chave escondida -- e a forma padrao de executar um modulo de teste
    --, mas quem produz baseline para valer produz por `executar.py`.
    Por esse caminho o contrato de saida TAMBEM nao vale, porque quem
    escolhe o codigo e o `unittest`: credencial ausente ou recusada,
    aplicacao fora do ar e navegador ausente (falhas na preparacao da
    classe) saem 5, e matriz de rotas ou configuracao invalida (erro ao
    importar o modulo) sai 1 -- o codigo de "achei violacao" para "nao
    consigo executar". So `executar.py` traduz esses casos para 2.
  * A marcacao de registro INSTAVEL existe e e contada, mas nunca foi
    exercitada por um caso real: neste fixture nada oscila. Em aplicacao com
    dado vivo ela e o primeiro numero a conferir.
  RECURSO COMPLEMENTAR para o que fica descoberto: as capturas de tela gravadas
  das rotas com achado, para revisao humana.
"""

from __future__ import annotations

import json
import os
import re
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright

from uiguards.common import GuardCannotRun, load_config, optional, require
from uiguards.overflow import (
    ORDEM_ESPECIES, assentar, config_de_medicao, conjunto_do_placar, medir,
)

RAIZ = Path(__file__).resolve().parent.parent


def validar_rotas(rotas: dict) -> dict:
    """
    Confere a matriz de rotas ANTES de medir qualquer coisa. Tipo errado,
    chave ausente e matriz vazia sao configuracao invalida: 2.

    Matriz sem viewport ou sem area mede nada, e medir nada nao e base
    limpa: a assinatura sairia vazia e fixavel. Uma area declarada sem rota
    nenhuma e o mesmo engano em escala menor.
    """
    base = require(rotas, "base", "rotas", "tabela")
    require(base, "url", "base", "texto", nao_vazio=True)
    vp_res = require(base, "viewport_de_resolucao", "base", "texto")
    viewports = require(rotas, "viewport", "rotas", "lista de tabelas", nao_vazio=True)
    nomes = []
    for i, vp in enumerate(viewports):
        onde = f"viewport #{i + 1}"
        nomes.append(require(vp, "nome", onde, "texto", nao_vazio=True))
        require(vp, "largura", onde, "inteiro")
        require(vp, "altura", onde, "inteiro")
        optional(vp, "piso_de_estresse", onde, "booleano", False)
    if len(set(nomes)) != len(nomes):
        raise GuardCannotRun(f"nomes de viewport repetidos em rotas: {nomes}")
    if vp_res not in nomes:
        raise GuardCannotRun(
            f"viewport_de_resolucao '{vp_res}' nao e nenhum dos viewports declarados: {nomes}")
    areas = require(rotas, "area", "rotas", "lista de tabelas", nao_vazio=True)
    for i, area in enumerate(areas):
        onde = f"area #{i + 1}"
        require(area, "nome", onde, "texto", nao_vazio=True)
        require(area, "com_sessao", onde, "booleano")
        if "lista" in area:
            require(area, "lista", onde, "texto", nao_vazio=True)
            require(area, "seletor_de_identificadores", onde, "texto", nao_vazio=True)
            if require(area, "minimo_esperado", onde, "inteiro") < 1:
                raise GuardCannotRun(f"minimo_esperado precisa ser ao menos 1 em [{onde}]")
        else:
            require(area, "rotas", onde, "lista de textos", nao_vazio=True)
    for i, f in enumerate(optional(rotas, "fora_de_escopo", "rotas", "lista de tabelas", [])):
        require(f, "rota", f"fora_de_escopo #{i + 1}", "texto")
        require(f, "motivo", f"fora_de_escopo #{i + 1}", "texto", nao_vazio=True)
    return rotas


CFG = load_config(RAIZ / "guards.toml")
ROTAS = validar_rotas(load_config(RAIZ / os.environ.get("VARREDURA_ROTAS", "rotas.toml")))

PISO, LIMITE, ANCORAS = config_de_medicao(CFG)

# Identificador unico da execucao, fornecido EXTERNAMENTE. Sem ele, o parcial
# registra um rotulo de ausencia -- nunca um valor inventado -- e o GUARD 6
# recusa a execucao que nao informou identificador.
SENTINELA_ID = "SEM-IDENTIFICADOR"
ID_EXECUCAO = os.environ.get("VARREDURA_ID", SENTINELA_ID)
# O padrao NAO e o diretorio da baseline fixada (out/varredura): medir de
# novo sem informar a saida nao pode sobrescreve-la.
SAIDA = Path(os.environ.get("VARREDURA_SAIDA", RAIZ / "out" / "medicao"))
BASE_URL = os.environ.get("FIXTURE_BASE_URL", ROTAS["base"]["url"]).rstrip("/")

JANELA_CONVERGENCIA = 5   # leituras ate desistir e marcar o registro instavel
TENTATIVAS_DESTINO = 4    # distingue navegacao lenta de redirecionamento real


def _slug(rota: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", rota.lower()).strip("_") or "raiz"


def credenciais() -> tuple[str, str]:
    """
    Credenciais SEMPRE por variavel de ambiente, nunca embutidas.

    Ausencia de credencial e ENTRADA AUSENTE: codigo 2, nunca 0 e nunca 1.
    Pular o teste seria pior que falhar: `unittest` conta teste pulado como
    sucesso, e a suite sairia VERDE tendo medido zero rota -- um gate que
    aprova por nao ter conseguido rodar. E o modo de falha que o contrato
    comum existe para impedir.
    """
    usuario, senha = os.environ.get("FIXTURE_USUARIO"), os.environ.get("FIXTURE_SENHA")
    if not usuario or not senha:
        faltando = [n for n in ("FIXTURE_USUARIO", "FIXTURE_SENHA")
                    if not os.environ.get(n)]
        raise GuardCannotRun(
            f"credenciais ausentes no ambiente: {', '.join(faltando)}. "
            "As areas com sessao nao podem ser medidas, e medir so as publicas "
            "produziria uma baseline silenciosamente parcial.\n"
            "  informe as credenciais: export FIXTURE_USUARIO=<usuario> "
            "FIXTURE_SENHA=<senha>")
    return usuario, senha


def autenticar(ctx, base: str) -> None:
    """
    Abre a sessao com as credenciais do ambiente.

    Credencial PRESENTE mas recusada e entrada invalida, nao violacao: nenhuma
    rota chegou a ser medida. Sem esta traducao, a recusa chegava ao ponto de
    entrada como erro de teste e saia como 1 ("achei violacao") sob a linha
    "VARREDURA REPROVADA" -- com um tempo limite do navegador no lugar da
    causa. Uma senha rotacionada viraria "violacao de layout" no CI.
    """
    usuario, senha = credenciais()
    pg = ctx.new_page()
    try:
        pg.goto(f"{base}/login", wait_until="domcontentloaded")
        pg.fill("input[name=usuario]", usuario)
        pg.fill("input[name=senha]", senha)
        pg.click("button[type=submit]")
        pg.wait_for_url(f"{base}/", timeout=10_000)
    except Exception as exc:  # noqa: BLE001
        raise GuardCannotRun(
            f"nao consegui autenticar em {base}/login com as credenciais do "
            f"ambiente (FIXTURE_USUARIO={usuario!r}): {type(exc).__name__}. "
            "Nenhuma rota foi medida -- isto e entrada invalida, nao violacao.\n"
            "  confira as credenciais e se a aplicacao esta no ar em "
            f"{base}") from exc
    finally:
        pg.close()


def conferir_estado_inicial(page) -> dict:
    """
    ESTADO INICIAL VERIFICAVEL.

    O teste fixa movimento reduzido e esquema de cor claro por configuracao do
    contexto; aqui ele CONFIRMA, medindo a propriedade resultante na propria
    pagina, que a configuracao pegou -- e aborta alto se nao pegou.
    Configuracao aceita em silencio produz baseline verde medida no estado
    errado, e duas execucoes concordam entre si, o que torna o erro invisivel.
    """
    estado = page.evaluate("""() => ({
        movimento_reduzido: matchMedia('(prefers-reduced-motion: reduce)').matches,
        esquema_escuro: matchMedia('(prefers-color-scheme: dark)').matches,
    })""")
    if not estado["movimento_reduzido"] or estado["esquema_escuro"]:
        raise AssertionError(
            "ABORTANDO ALTO: o estado inicial NAO foi aplicado na pagina "
            f"(medido: {estado}). Esperava movimento reduzido ativo e esquema "
            "claro. Medir neste estado produziria baseline verde no estado errado.")
    return estado


def navegar_validando_destino(page, url: str, caminho_esperado: str) -> tuple[str, int | None]:
    """
    VALIDACAO DE DESTINO: terminada a navegacao, o endereco final precisa
    coincidir com o pedido. Se nao coincidir, o teste do viewport FALHA e nenhuma medicao dessa
    rota e gravada.

    Justificativa: sessao expirada ou redirecionamento fazem a navegacao
    terminar noutra pagina, e sem esta conferencia os defeitos dessa outra
    pagina seriam gravados com o nome da rota pedida.

    Navegacao apenas lenta chega ao destino se esperada mais um pouco; por
    isso ha novas conferencias com espera crescente. Um redirecionamento de
    fato continua no lugar errado em todas elas, e falha.

    Devolve tambem o status HTTP da resposta principal da navegacao (None se
    o navegador nao entregou resposta), para quem chama decidir se a rota
    pode ser medida.
    """
    ultimo, status = "", None
    for tentativa in range(TENTATIVAS_DESTINO):
        if tentativa == 0:
            resposta = page.goto(url, wait_until="domcontentloaded")
            status = resposta.status if resposta is not None else None
        else:
            page.wait_for_timeout(150 * tentativa)
        ultimo = re.sub(r"[?#].*$", "", page.url[len(BASE_URL):]) or "/"
        if ultimo.rstrip("/") == caminho_esperado.rstrip("/") or (
                ultimo == "/" and caminho_esperado == "/"):
            return ultimo, status
    raise AssertionError(
        f"DESTINO DIVERGENTE apos {TENTATIVAS_DESTINO} tentativas: pedi "
        f"'{caminho_esperado}', terminei em '{ultimo}'. O teste falha aqui: "
        "gravar a pagina de chegada com o nome da rota pedida atribuiria a ela "
        "defeitos de outra pagina.")


def motivo_nao_medivel(status: int | None) -> str | None:
    """
    A rota pode ser medida? Decide SO pelo status HTTP da resposta principal,
    nunca pelo que a pagina mostra: 4xx ou 5xx no proprio endereco, ou
    nenhuma resposta principal entregue pelo navegador, torna a rota nao
    medivel. Qualquer outro status -- inclusive uma pagina de erro entregue
    com 200 -- e medido como a propria rota.
    """
    if status is None:
        return "o navegador nao entregou resposta principal para a navegacao"
    if status >= 400:
        return f"a resposta principal do proprio endereco foi HTTP {status}"
    return None


def medir_estabilizado(page) -> tuple[dict, bool, int]:
    """
    MEDICAO ESTABILIZADA: le a pagina repetidas vezes e fica com a primeira
    leitura cujo placar -- o CONJUNTO de (especie, seletor) -- e igual ao da
    leitura anterior.

    Excedentes em pixels ficam fora da comparacao: o mesmo defeito pode variar
    uma fracao de pixel entre leituras, e compara-los esgotaria a janela sem
    motivo. Esgotada a janela, o registro sai marcado como INSTAVEL, e o
    relatorio diz quantos houve.
    """
    assentar(page)
    anterior = medir(page, PISO, LIMITE, ANCORAS)
    for leitura_n in range(2, JANELA_CONVERGENCIA + 1):
        assentar(page)
        atual = medir(page, PISO, LIMITE, ANCORAS)
        if conjunto_do_placar(atual) == conjunto_do_placar(anterior):
            return atual, True, leitura_n
        anterior = atual
    return anterior, False, JANELA_CONVERGENCIA


def resolver_identificadores(ctx, area: dict, largura: int, altura: int) -> list[str]:
    """
    Colhe os caminhos das fichas de detalhe uma vez so, no viewport
    `viewport_de_resolucao`; os demais viewports recebem essa mesma lista.

    Na aplicacao de exemplo, a tabela de clientes esconde linhas abaixo de
    768 px: colhendo em cada largura, o celular levaria tres fichas e o
    desktop cinco.
    """
    pg = ctx.new_page()
    pg.set_viewport_size({"width": largura, "height": altura})
    _destino, status = navegar_validando_destino(pg, BASE_URL + area["lista"], area["lista"])
    if status is None or status >= 400:
        raise AssertionError(
            f"a lista '{area['lista']}' que resolve as paginas de detalhe respondeu "
            f"{'sem resposta principal' if status is None else f'HTTP {status}'}: "
            "nao ha de onde tirar os identificadores.")
    assentar(pg)
    # Somente o que o viewport de resolucao REALMENTE renderiza. Casar o
    # seletor CSS sem olhar a renderizacao acharia tambem as linhas que a
    # folha de estilo esconde na largura menor -- e a resolucao deixaria de
    # depender do viewport, que e justamente o que se quer fixar.
    hrefs = pg.eval_on_selector_all(
        area["seletor_de_identificadores"],
        "els => els.filter(e => e.getClientRects().length > 0)"
        ".map(e => new URL(e.href).pathname)")
    pg.close()
    return sorted(set(hrefs))


class VarreduraBase(unittest.TestCase):
    """Um metodo de teste por viewport e gerado dinamicamente abaixo."""

    @classmethod
    def setUpClass(cls):
        cls._pw = sync_playwright().start()
        cls._nav = cls._pw.chromium.launch()
        SAIDA.mkdir(parents=True, exist_ok=True)
        (SAIDA / "capturas").mkdir(exist_ok=True)

        vp_res = next(v for v in ROTAS["viewport"]
                      if v["nome"] == ROTAS["base"]["viewport_de_resolucao"])
        ctx = cls._nav.new_context(
            viewport={"width": vp_res["largura"], "height": vp_res["altura"]},
            reduced_motion="reduce", color_scheme="light")
        autenticar(ctx, BASE_URL)
        cls._estado_sessao = ctx.storage_state()

        cls._identificadores = {}
        for area in ROTAS["area"]:
            if "lista" in area:
                cls._identificadores[area["nome"]] = resolver_identificadores(
                    ctx, area, vp_res["largura"], vp_res["altura"])
        ctx.close()
        cls._viewport_resolucao = vp_res["nome"]

    @classmethod
    def tearDownClass(cls):
        cls._nav.close()
        cls._pw.stop()

    def _contexto(self, vp: dict, com_sessao: bool):
        return self._nav.new_context(
            viewport={"width": vp["largura"], "height": vp["altura"]},
            reduced_motion="reduce",          # sem animacao, a largura nao depende do instante lido
            color_scheme="light",
            storage_state=self._estado_sessao if com_sessao else None)

    def varrer_viewport(self, vp: dict):
        registros, instaveis = [], 0
        rotas_medidas = []

        for area in ROTAS["area"]:
            if "lista" in area:
                ids = self._identificadores[area["nome"]]
                # COBERTURA DE DETALHE: menos paginas que o minimo declarado reprova
                self.assertGreaterEqual(
                    len(ids), int(area["minimo_esperado"]),
                    f"cobertura de paginas de detalhe encolheu: resolvi {len(ids)} "
                    f"em '{area['nome']}', esperava ao menos {area['minimo_esperado']}. "
                    f"(resolucao feita no viewport '{self._viewport_resolucao}')")
                alvos = ids
            else:
                alvos = list(area["rotas"])

            ctx = self._contexto(vp, bool(area["com_sessao"]))
            page = ctx.new_page()
            try:
                # O estado inicial e conferido na primeira rota da propria area: a
                # propriedade lida vale para o contexto inteiro, e uma rota da matriz
                # existe em qualquer projeto, ao contrario de uma rota fixa aqui.
                page.goto(BASE_URL + (alvos[0] if alvos else "/"),
                          wait_until="domcontentloaded")
                conferir_estado_inicial(page)
                for rota in alvos:
                    destino, status = navegar_validando_destino(page, BASE_URL + rota, rota)
                    rotas_medidas.append(rota)
                    motivo = motivo_nao_medivel(status)
                    if motivo:
                        # A pagina de erro que vem no lugar renderiza e poderia
                        # ser medida, mas nao e a pagina da rota: o registro
                        # sai sem medicao, marcado, e o GUARD 6 o conta como
                        # rota quebrada.
                        registros.append({
                            "area": area["nome"],
                            "rota": rota,
                            "destino_esperado": rota,
                            "destino_final": destino,
                            "nao_medivel": True,
                            "motivo_nao_medivel": motivo,
                            "achados": [],
                        })
                        continue
                    leitura, estavel, n_leituras = medir_estabilizado(page)
                    instaveis += 0 if estavel else 1
                    captura = None
                    if leitura["placar"] > 0:
                        # capturas apenas das rotas com achado, para revisao humana
                        nome = f"{vp['nome']}-{_slug(rota)}.png"
                        page.screenshot(path=str(SAIDA / "capturas" / nome), full_page=True)
                        captura = f"capturas/{nome}"
                    achados = [a for nome in ORDEM_ESPECIES
                               for a in leitura["especies"].get(nome, [])]
                    registros.append({
                        "area": area["nome"],
                        "rota": rota,
                        "destino_esperado": rota,
                        "destino_final": destino,
                        "estavel": estavel,
                        "leituras_ate_convergir": n_leituras,
                        "placar": leitura["placar"],
                        "metricas": leitura["metricas"],
                        "abaixo_do_piso": leitura["abaixo_do_piso"],
                        "achados": achados,
                        "captura": captura,
                    })
            finally:
                ctx.close()

        registros.sort(key=lambda r: (r["area"], r["rota"]))
        parcial = {
            "identificador_execucao": ID_EXECUCAO,
            "viewport": {"nome": vp["nome"], "largura": vp["largura"],
                         "altura": vp["altura"],
                         "piso_de_estresse": bool(vp.get("piso_de_estresse", False))},
            "escopo_aplicado": {
                "areas": [a["nome"] for a in ROTAS["area"]],
                "rotas_medidas": sorted(rotas_medidas),
                "viewport_de_resolucao_de_detalhe": self._viewport_resolucao,
                "identificadores_de_detalhe": self._identificadores,
                "piso_severidade_px": PISO,
                "ancoras": ANCORAS,
                "fora_de_escopo": sorted(
                    ({"rota": f["rota"], "motivo": f["motivo"]}
                     for f in ROTAS.get("fora_de_escopo", [])),
                    key=lambda f: f["rota"]),
            },
            "instaveis": instaveis,
            "registros": registros,
        }
        destino = SAIDA / f"parcial-{vp['nome']}.json"
        destino.write_text(
            json.dumps(parcial, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8")
        print(f"\n    {vp['nome']:18} {len(registros):2d} rotas | "
              f"placar {sum(r.get('placar', 0) for r in registros):3d} | "
              f"nao mediveis {sum(1 for r in registros if r.get('nao_medivel'))} | "
              f"instaveis {instaveis} | -> {destino.name}")


def _montar_testes():
    for vp in ROTAS["viewport"]:
        def teste(self, vp=vp):
            self.varrer_viewport(vp)
        teste.__doc__ = (f"varre o viewport {vp['nome']} "
                         f"({vp['largura']}x{vp['altura']}) e grava o seu parcial")
        setattr(VarreduraBase, f"test_viewport_{vp['nome'].replace('-', '_')}", teste)


_montar_testes()

if __name__ == "__main__":
    unittest.main(verbosity=2)
