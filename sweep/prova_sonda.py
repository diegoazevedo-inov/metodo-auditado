"""
PROVA DO GUARD 4 -- a sonda de estouro por elemento.

O ponto de entrada da suite (sweep/executar.py) roda esta prova antes da
varredura (GUARD 5): se ela nao passar, nenhuma medicao e gravada.

Depois de cada plantio a sonda e lida de novo, em laco e com prazo, ate o
resultado esperado aparecer. Uma pausa de duracao fixa bastaria numa maquina
folgada e falharia de vez em quando numa ocupada -- a prova ficaria
intermitente por causa dela mesma.
"""

from __future__ import annotations

import os
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402

from uiguards.common import load_config  # noqa: E402
from uiguards.overflow import assentar, medir  # noqa: E402

BASE = os.environ.get("FIXTURE_BASE_URL", "http://127.0.0.1:8731")
CFG = load_config(Path(__file__).resolve().parent.parent / "guards.toml")
PISO = float(CFG["medicao"]["piso_severidade_px"])
LIMITE = int(CFG["medicao"]["limite_por_especie"])
ESPERA_S = 6.0


class ProvaSonda(unittest.TestCase):
    """Fabrica na pagina um caso de CADA especie e de cada isencao, e confere o que a sonda diz."""

    @classmethod
    def setUpClass(cls):
        cls._pw = sync_playwright().start()
        cls._nav = cls._pw.chromium.launch()
        cls._ctx = cls._nav.new_context(
            viewport={"width": 390, "height": 844}, reduced_motion="reduce")
        cls.page = cls._ctx.new_page()
        cls.page.goto(f"{BASE}/publico/precos", wait_until="domcontentloaded")
        assentar(cls.page)

    @classmethod
    def tearDownClass(cls):
        cls._nav.close()
        cls._pw.stop()

    # -- utilidades ------------------------------------------------------
    def plantar(self, html: str):
        # A prova do detector NAO pode depender das ancoras do GUARD 6: se ela
        # dependesse, renomear uma ancora reprovaria o instrumento em vez de
        # exercitar o guard de ancora.
        self.page.evaluate(
            "(h) => (document.querySelector('[data-ui-content]') || document.body)"
            ".insertAdjacentHTML('beforeend', h)", html)

    def remover(self, ident: str):
        self.page.evaluate(f"() => document.getElementById('{ident}')?.remove()")

    def exigir_plantado(self, ident: str):
        """
        Uma prova NEGATIVA ("nao acusa") so prova alguma coisa se o plantio
        existe E TEM O QUE SER ACUSADO. Sem a primeira conferencia ela passa
        vacua com o plantio desligado (as provas 03 e 08 continuavam verdes
        sobre elemento ausente); sem a segunda, passa vacua com um plantio
        presente mas inerte -- um filho que deixou de ser largo nao transborda,
        e a ausencia de achado volta a ser trivial.
        """
        medida = self.page.evaluate(
            f"""() => {{ const e = document.getElementById('{ident}');
                 return e ? {{sw: e.scrollWidth, cw: e.clientWidth}} : null; }}""")
        self.assertIsNotNone(
            medida,
            f"o plantio #{ident} nao esta na pagina: a prova negativa seria vacua")
        excedente = medida["sw"] - medida["cw"]
        self.assertGreaterEqual(
            excedente, PISO,
            f"#{ident} existe mas nao transborda (excedente {excedente}px, piso "
            f"{PISO}px): sem excedente acima do piso nao ha o que isentar, e a "
            "prova negativa seria vacua")

    def ler_ate(self, condicao, descricao: str):
        """Le a sonda de novo, em laco e com prazo, ate o resultado esperado aparecer."""
        limite = time.monotonic() + ESPERA_S
        leitura = None
        while time.monotonic() < limite:
            assentar(self.page)
            leitura = medir(self.page, PISO, LIMITE)
            if condicao(leitura):
                return leitura
            self.page.wait_for_timeout(50)
        self.fail(f"condicao nunca valeu em {ESPERA_S}s: {descricao}\n"
                  f"ultima leitura: {self._resumo(leitura)}")

    @staticmethod
    def _achados(leitura, so_placar=False):
        return [a for grupo in leitura["especies"].values() for a in grupo
                if a["no_placar"] or not so_placar]

    @classmethod
    def _seletores(cls, leitura, so_placar=False):
        return {a["seletor"] for a in cls._achados(leitura, so_placar)}

    @staticmethod
    def _resumo(leitura):
        if leitura is None:
            return "(nenhuma)"
        return ", ".join(f"{a['especie']}:{a['seletor']}"
                         for g in leitura["especies"].values() for a in g) or "(vazia)"

    def _especie_de(self, leitura, seletor):
        for a in self._achados(leitura):
            if a["seletor"] == seletor:
                return a
        return None

    # -- provas ----------------------------------------------------------
    def test_01_elemento_largo_sem_contencao_aparece_pelo_seletor(self):
        """O achado tem de trazer o seletor do plantio; um total maior nao diz qual elemento foi achado."""
        self.plantar('<div id="plantio-largo"><div style="width:2000px">largo</div></div>')
        leitura = self.ler_ate(
            lambda l: "#plantio-largo" in self._seletores(l, so_placar=True),
            "#plantio-largo no placar")
        achado = self._especie_de(leitura, "#plantio-largo")
        print(f"\n  [01] NOMEADO: {achado['seletor']} especie={achado['especie']} "
              f"excedente={achado['excedente']}px "
              f"filho_responsavel={achado['filho_responsavel']}")
        self.assertTrue(achado["no_placar"])
        # A especie e exigida pelo nome: sem isto, uma sonda que nunca
        # produzisse `transbordo-visivel` passaria pela prova inteira.
        self.assertEqual(achado["especie"], "transbordo-visivel")

    def test_02_plantio_removido_sai_dos_achados(self):
        """
        Confere que o seletor do plantio sumiu dos achados. Nao compara o
        total de achados com o de antes: numa pagina real, algum achado
        perto do piso pode aparecer numa leitura e nao na outra.
        """
        self.remover("plantio-largo")
        self.ler_ate(lambda l: "#plantio-largo" not in self._seletores(l),
                     "#plantio-largo ausente")
        print("  [02] plantio removido: nao aparece mais (conferido pelo seletor "
              "do plantio, nao pela contagem)")

    def test_03_dentro_de_rolagem_horizontal_declarada_NAO_acusa(self):
        self.plantar('<div id="plantio-rol-h" class="overflow-x-auto">'
                     '<div style="width:2000px">conteudo largo</div></div>')
        self.exigir_plantado("plantio-rol-h")
        leitura = self.ler_ate(
            lambda l: any("plantio-rol-h" in s for s in self._seletores(l)) is False
            and l["metricas"]["elementos_examinados"] > 0,
            "nenhum achado sob #plantio-rol-h")
        self.assertFalse(any("plantio-rol-h" in s for s in self._seletores(leitura)))
        print("  [03] rolagem horizontal DECLARADA: nao acusou (isencao pela classe)")
        self.remover("plantio-rol-h")

    def test_04_dentro_de_rolagem_VERTICAL_ACUSA(self):
        """
        Prova central da decisao de classificacao (ver o cabecalho da sonda).

        Com rolagem so na vertical, o contentor tambem fica com `overflow-x`
        diferente de `visible`. Se a especie dependesse dos ancestrais, o
        plantio passaria por resolvido e o defeito real ficaria fora do
        relatorio.
        """
        self.plantar('<div id="plantio-rol-v" class="overflow-y-auto" style="height:80px">'
                     '<div id="plantio-rol-v-interno">'
                     '<div style="width:2000px">conteudo largo</div></div></div>')
        leitura = self.ler_ate(
            lambda l: "#plantio-rol-v-interno" in self._seletores(l, so_placar=True),
            "#plantio-rol-v-interno no placar")
        achado = self._especie_de(leitura, "#plantio-rol-v-interno")
        externo = self._especie_de(leitura, "#plantio-rol-v")
        print(f"  [04] ROLAGEM VERTICAL NAO ISENTA: {achado['seletor']} "
              f"especie={achado['especie']} excedente={achado['excedente']}px "
              f"NO PLACAR={achado['no_placar']}")
        print(f"       (o contentor externo #plantio-rol-v saiu como "
              f"'{externo['especie'] if externo else '-'}', "
              f"no_placar={externo['no_placar'] if externo else '-'})")
        self.assertTrue(achado["no_placar"])
        self.remover("plantio-rol-v")

    def test_05_recorte_de_conteudo_real(self):
        self.plantar('<div id="plantio-recorte" style="overflow:hidden;width:200px">'
                     '<div style="width:900px">coluna de conteudo que some</div></div>')
        leitura = self.ler_ate(
            lambda l: (self._especie_de(l, "#plantio-recorte") or {}).get("especie")
            == "recorte-sem-rolagem", "#plantio-recorte como recorte real")
        achado = self._especie_de(leitura, "#plantio-recorte")
        print(f"  [05] recorte de conteudo: especie={achado['especie']} "
              f"no_placar={achado['no_placar']}")
        self.assertTrue(achado["no_placar"])
        self.remover("plantio-recorte")

    def test_06_recorte_de_pura_decoracao_fica_FORA_do_placar(self):
        self.plantar(
            '<div id="plantio-deco" style="overflow:hidden;width:200px;'
            'height:40px;position:relative">'
            '<div aria-hidden="true" style="position:absolute;left:0;top:0;'
            'width:900px;height:6px;background:#ccc"></div></div>')
        leitura = self.ler_ate(
            lambda l: (self._especie_de(l, "#plantio-deco") or {}).get("especie")
            == "recorte-decorativo", "#plantio-deco como decorativo")
        achado = self._especie_de(leitura, "#plantio-deco")
        print(f"  [06] recorte decorativo: especie={achado['especie']} "
              f"no_placar={achado['no_placar']} (a decorativa fica fora da "
              f"contagem)")
        self.assertFalse(achado["no_placar"])
        self.assertNotIn("#plantio-deco", self._seletores(leitura, so_placar=True))
        self.remover("plantio-deco")

    def test_07_truncamento_com_variante_de_ponto_de_quebra_NAO_isenta(self):
        """Abaixo do ponto de quebra a variante nao se aplica, e o estouro aparece ali."""
        self.plantar('<div id="plantio-trunc-md" class="md:truncate" '
                     'style="white-space:nowrap">'
                     'razao social muito comprida que nao cabe na largura do celular</div>')
        leitura = self.ler_ate(
            lambda l: "#plantio-trunc-md" in self._seletores(l, so_placar=True),
            "#plantio-trunc-md no placar")
        achado = self._especie_de(leitura, "#plantio-trunc-md")
        print(f"  [07] 'md:truncate' NAO isentou em viewport 390: "
              f"especie={achado['especie']} excedente={achado['excedente']}px")
        self.assertEqual(achado["especie"], "transbordo-visivel")
        self.remover("plantio-trunc-md")

    def test_08_truncamento_declarado_sem_variante_ISENTA(self):
        """Mesma logica da rolagem declarada: truncar sem condicao e intencao."""
        self.plantar('<div id="plantio-trunc" class="truncate">'
                     'razao social muito comprida que nao cabe na largura do celular</div>')
        self.exigir_plantado("plantio-trunc")
        leitura = self.ler_ate(
            lambda l: "#plantio-trunc" not in self._seletores(l),
            "#plantio-trunc isento")
        print("  [08] 'truncate' sem variante: isentou (intencao declarada)")
        self.assertNotIn("#plantio-trunc", self._seletores(leitura))
        self.remover("plantio-trunc")

    def test_09_rolagem_horizontal_NAO_declarada_e_acusada(self):
        """
        A quarta especie. Ha rolagem horizontal (overflow-x computado `auto`)
        mas nenhuma classe a declarou como intencao: e a pagina "andando de
        lado" sem que ninguem tenha pedido. Entra no placar.
        """
        self.plantar('<div id="plantio-rol-nd" style="overflow-x:auto;width:200px">'
                     '<div style="width:900px">conteudo que rola sem ninguem pedir</div></div>')
        leitura = self.ler_ate(
            lambda l: (self._especie_de(l, "#plantio-rol-nd") or {}).get("especie")
            == "rolagem-nao-declarada", "#plantio-rol-nd como rolagem nao declarada")
        achado = self._especie_de(leitura, "#plantio-rol-nd")
        print(f"  [09] rolagem NAO declarada: especie={achado['especie']} "
              f"no_placar={achado['no_placar']}")
        self.assertTrue(achado["no_placar"])
        self.remover("plantio-rol-nd")

    def test_10_variante_de_ponto_de_quebra_na_rolagem_NAO_isenta(self):
        """
        A regra do teste 07, aplicada a rolagem. `md:overflow-x-auto` e
        inativo em 390px; o contentor so tem overflow-x `auto` por efeito
        colateral da rolagem VERTICAL. Uma classe que nao se aplica nao pode isentar.
        """
        self.plantar('<div id="plantio-rol-md" class="md:overflow-x-auto overflow-y-auto" '
                     'style="height:60px"><div style="width:2000px">coluna que some</div></div>')
        leitura = self.ler_ate(
            lambda l: "#plantio-rol-md" in self._seletores(l, so_placar=True),
            "#plantio-rol-md no placar")
        achado = self._especie_de(leitura, "#plantio-rol-md")
        print(f"  [10] 'md:overflow-x-auto' NAO isentou em viewport 390: "
              f"especie={achado['especie']} excedente={achado['excedente']}px")
        self.assertEqual(achado["especie"], "rolagem-nao-declarada")
        self.remover("plantio-rol-md")

    def test_12_oculto_acessivel_com_variante_de_ponto_de_quebra_NAO_isenta(self):
        """
        Terceira isencao, mesma regra das outras duas. `md:sr-only` nao se
        aplica em 390px: o conteudo esta recortado de verdade nessa largura.
        """
        self.plantar('<div id="plantio-sr-md" class="md:sr-only" '
                     'style="overflow:hidden;width:200px">'
                     '<div style="width:900px">conteudo recortado de verdade</div></div>')
        leitura = self.ler_ate(
            lambda l: "#plantio-sr-md" in self._seletores(l, so_placar=True),
            "#plantio-sr-md no placar")
        achado = self._especie_de(leitura, "#plantio-sr-md")
        print(f"  [12] 'md:sr-only' NAO isentou em viewport 390: "
              f"especie={achado['especie']} excedente={achado['excedente']}px")
        self.assertTrue(achado["no_placar"])
        self.remover("plantio-sr-md")

    # Os tres seguintes sao o outro lado do teste 06: filho sem texto que NAO
    # e enfeite. Campo, botao e imagem cortados sao conteudo que some para
    # quem usa, e tem de ficar no placar.
    def _exigir_recorte_real(self, ident: str, rotulo: str, num: str):
        leitura = self.ler_ate(
            lambda l: (self._especie_de(l, f"#{ident}") or {}).get("especie")
            == "recorte-sem-rolagem", f"#{ident} como recorte real")
        achado = self._especie_de(leitura, f"#{ident}")
        print(f"  [{num}] {rotulo}: especie={achado['especie']} "
              f"no_placar={achado['no_placar']} excedente={achado['excedente']}px")
        self.assertTrue(achado["no_placar"])
        self.assertIn(f"#{ident}", self._seletores(leitura, so_placar=True))
        self.remover(ident)

    def test_13_campo_de_formulario_cortado_e_recorte_real_NO_placar(self):
        self.plantar('<div id="plantio-campo" style="overflow:hidden;width:200px">'
                     '<input aria-label="busca" style="width:900px"></div>')
        self._exigir_recorte_real("plantio-campo", "campo <input> cortado, sem texto", "13")

    def test_14_imagem_cortada_e_recorte_real_NO_placar(self):
        self.plantar('<div id="plantio-imagem" style="overflow:hidden;width:200px">'
                     '<img alt="grafico de vendas" style="display:block;width:900px;height:20px" '
                     'src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7">'
                     '</div>')
        self._exigir_recorte_real("plantio-imagem", "imagem <img> cortada", "14")

    def test_15_fileira_sem_texto_com_botao_de_icone_e_recorte_real_NO_placar(self):
        """O filho que transborda e um involucro sem texto; o botao esta DENTRO dele."""
        self.plantar('<div id="plantio-fileira" style="overflow:hidden;width:200px">'
                     '<div style="display:flex;width:900px"><span style="flex:1"></span>'
                     '<button aria-label="Excluir" style="width:40px;height:24px">'
                     '<svg width="16" height="16" aria-hidden="true"></svg></button></div></div>')
        self._exigir_recorte_real(
            "plantio-fileira", "fileira sem texto com botao so de icone dentro", "15")

    def test_16_oculto_acessivel_isenta_por_ser_a_tecnica_nao_pelo_tamanho(self):
        """
        O `sr-only` da moldura (teste 11) mede 1px e ja sai pelo corte de caixa
        desprezivel, antes de chegar a isencao: o teste 11 passa mesmo sem ela.
        Aqui a caixa tem tamanho normal e transborda de verdade, entao so a
        ISENCAO pela classe a tira dos achados.
        """
        self.plantar('<div id="plantio-sr" class="sr-only" style="position:static;'
                     'width:200px;height:40px;clip-path:none">'
                     '<div style="width:900px">texto so para leitor de tela</div></div>')
        self.exigir_plantado("plantio-sr")
        leitura = self.ler_ate(lambda l: "#plantio-sr" not in self._seletores(l),
                               "#plantio-sr isento pela classe")
        print(f"  [16] 'sr-only' com caixa de 200px e excedente real: isento pela classe "
              f"(isentos na leitura: {leitura['ignorados_por_isencao']})")
        self.assertNotIn("#plantio-sr", self._seletores(leitura))
        self.remover("plantio-sr")

    # Os quatro seguintes sao os lados do criterio decorativo: o filho que o
    # corte esconde e CONTEUDO se for interativo, se tiver texto visivel, ou se
    # for imagem ou grafico sem aria-hidden; fora isso, e decoracao.
    def test_17_texto_visivel_cortado_e_conteudo_mesmo_com_os_sinais_de_enfeite(self):
        """Posicao absoluta, pointer-events e aria-hidden nao desfazem o texto visivel."""
        casos = {
            "plantio-txt-abs": '<span style="position:absolute;left:0;top:0;white-space:nowrap">',
            "plantio-txt-pe": '<span style="pointer-events:none;display:block;width:900px">',
            "plantio-txt-ah": '<span aria-hidden="true" style="display:block;width:900px">',
        }
        for ident, abre in casos.items():
            self.plantar(f'<div id="{ident}" style="position:relative;overflow:hidden;'
                         f'width:200px;height:40px">{abre}'
                         'Saldo devedor de R$ 12.345,67 com vencimento hoje ate as 18h'
                         '</span></div>')
            self._exigir_recorte_real(ident, f"texto visivel cortado ({ident[12:]})", "17")

    def test_18_campo_cortado_com_aria_hidden_e_conteudo(self):
        self.plantar('<div id="plantio-campo-ah" style="overflow:hidden;width:200px">'
                     '<input aria-hidden="true" style="width:900px"></div>')
        self._exigir_recorte_real("plantio-campo-ah", "campo cortado com aria-hidden", "18")

    def test_19_grafico_com_aria_hidden_sem_texto_e_decoracao(self):
        self.plantar('<div id="plantio-svg-ah" style="overflow:hidden;width:200px;height:40px">'
                     '<svg aria-hidden="true" width="900" height="20" style="display:block">'
                     '<rect width="900" height="20" fill="#ccc"></rect></svg></div>')
        leitura = self.ler_ate(
            lambda l: (self._especie_de(l, "#plantio-svg-ah") or {}).get("especie")
            == "recorte-decorativo", "#plantio-svg-ah como decorativo")
        achado = self._especie_de(leitura, "#plantio-svg-ah")
        print(f"  [19] grafico com aria-hidden, sem texto, cortado: especie={achado['especie']} "
              f"no_placar={achado['no_placar']}")
        self.assertFalse(achado["no_placar"])
        self.assertNotIn("#plantio-svg-ah", self._seletores(leitura, so_placar=True))
        self.remover("plantio-svg-ah")

    def test_20_imagem_sem_aria_hidden_e_conteudo_mesmo_fora_do_fluxo(self):
        self.plantar('<div id="plantio-img-abs" style="position:relative;overflow:hidden;'
                     'width:200px;height:40px">'
                     '<img alt="mapa da rota" style="position:absolute;left:0;top:0;'
                     'width:900px;height:20px" '
                     'src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7">'
                     '</div>')
        self._exigir_recorte_real("plantio-img-abs", "imagem sem aria-hidden, posicao absoluta", "20")

    def test_21_cadeia_aponta_o_ponto_acionavel(self):
        """O mais interno da cadeia e o que se corrige; o externo tem de apontar para ele."""
        self.plantar('<div id="plantio-cadeia-fora" style="overflow:hidden;width:200px">'
                     '<div id="plantio-cadeia-dentro" style="overflow:hidden;width:600px">'
                     '<div style="width:1400px">conteudo que some</div></div></div>')
        leitura = self.ler_ate(
            lambda l: self._especie_de(l, "#plantio-cadeia-fora") is not None
            and self._especie_de(l, "#plantio-cadeia-dentro") is not None,
            "os dois niveis da cadeia nos achados")
        fora = self._especie_de(leitura, "#plantio-cadeia-fora")
        dentro = self._especie_de(leitura, "#plantio-cadeia-dentro")
        print(f"  [21] cadeia: externo tem_achado_mais_interno={fora['tem_achado_mais_interno']} "
              f"filho_responsavel={fora['filho_responsavel']} | interno "
              f"tem_achado_mais_interno={dentro['tem_achado_mais_interno']}")
        self.assertTrue(fora["tem_achado_mais_interno"])
        self.assertFalse(dentro["tem_achado_mais_interno"])
        self.assertIsNotNone(fora["filho_responsavel"])
        self.assertIn("plantio-cadeia-dentro", fora["filho_responsavel"])
        self.remover("plantio-cadeia-fora")

    def _plantio_gerado(self, ident: str, css: str, filho_attrs: str = "",
                        dentro: str = ""):
        """Filho cortado, fora do fluxo e sem no de texto; o que ele mostra vem do estilo."""
        self.page.add_style_tag(content=css)
        self.plantar(f'<div id="{ident}" style="position:relative;overflow:hidden;'
                     f'width:200px;height:40px">'
                     f'<span id="{ident}-f" {filho_attrs} style="position:absolute;left:0;'
                     f'top:0;display:block;width:900px;height:20px">{dentro}</span></div>')

    def _exigir_decorativo(self, ident: str, rotulo: str, num: str):
        leitura = self.ler_ate(
            lambda l: (self._especie_de(l, f"#{ident}") or {}).get("especie")
            == "recorte-decorativo", f"#{ident} como decorativo")
        achado = self._especie_de(leitura, f"#{ident}")
        print(f"  [{num}] {rotulo}: especie={achado['especie']} no_placar={achado['no_placar']}")
        self.assertFalse(achado["no_placar"])
        self.remover(ident)

    def test_22_texto_gerado_pelo_estilo_e_conteudo(self):
        """Texto que o estilo poe na tela e perceptivel; glifo de icone sem aria-hidden e grafico."""
        casos = [
            ("plantio-g-before", "#plantio-g-before-f::before{content:'Saldo de R$ 12,00';white-space:nowrap}",
             "", "", "::before com texto"),
            ("plantio-g-after", "#plantio-g-after-f::after{content:'Saldo de R$ 12,00';white-space:nowrap}",
             "", "", "::after com texto"),
            ("plantio-g-desc", "#plantio-g-desc-n::before{content:'Saldo de R$ 12,00';white-space:nowrap}",
             "", '<span id="plantio-g-desc-n"></span>', "texto gerado num descendente"),
            ("plantio-g-attr", "#plantio-g-attr-f::before{content:attr(data-rotulo);white-space:nowrap}",
             'data-rotulo="Saldo de R$ 12,00"', "", "attr(), resolvido pelo navegador"),
            ("plantio-g-icone", "#plantio-g-icone-f::before{content:'\\e900'}",
             "", "", "glifo de icone sem aria-hidden"),
            ("plantio-g-urltexto", "#plantio-g-urltexto-f::before{content:'url(Saldo de R$ 12,00)';white-space:nowrap}",
             'aria-hidden="true"', "", "texto entre aspas que contem 'url(', com aria-hidden"),
            ("plantio-g-urlimg", "#plantio-g-urlimg-f::before{content:url(\"data:image/gif;base64,R0lGODlhAQABAAAAACw=\")}",
             "", "", "imagem por url() sem aria-hidden"),
            ("plantio-g-icdesc", "#plantio-g-icdesc-n::before{content:'\\e900'}",
             "", '<span id="plantio-g-icdesc-n"></span>', "glifo de icone num descendente, sem aria-hidden"),
            ("plantio-g-icrot", "#plantio-g-icrot-f::before{content:'\\e900'}#plantio-g-icrot-f::after{content:'Saldo de R$ 12,00';white-space:nowrap}",
             'aria-hidden="true"', "", "icone no ::before e rotulo no ::after, com aria-hidden"),
            ("plantio-g-escape", "#plantio-g-escape-f::before{content:'\\41 BC do saldo';white-space:nowrap}",
             'aria-hidden="true"', "", "escape que vira letra, com aria-hidden"),
            # Contrabarra LITERAL na tela: o CSS '\\20' mostra os tres caracteres \20.
            ("plantio-g-bs20", "#plantio-g-bs20-f::before{content:'\\\\20'}",
             "", "", "texto literal \\20, com a contrabarra visivel"),
            ("plantio-g-bsad", "#plantio-g-bsad-f::before{content:'\\\\AD'}",
             "", "", "texto literal \\AD, com a contrabarra visivel"),
            ("plantio-g-bse900", "#plantio-g-bse900-f::before{content:'\\\\e900'}",
             'aria-hidden="true"', "", "texto literal \\e900 com aria-hidden: e texto, nao icone"),
            ("plantio-g-xfade", "#plantio-g-xfade-f::before{content:-webkit-cross-fade("
             "url(\"data:image/gif;base64,R0lGODlhAQABAAAAACw=\"), "
             "url(\"data:image/gif;base64,R0lGODlhAQABAAAAACw=\"), 50%)}",
             "", "", "imagem por -webkit-cross-fade() sem aria-hidden"),
        ]
        for ident, css, attrs, dentro, rotulo in casos:
            with self.subTest(caso=ident):
                self._plantio_gerado(ident, css, attrs, dentro)
                self._exigir_recorte_real(ident, rotulo, "22")

    def test_23_estilo_que_nao_poe_texto_na_tela_continua_decoracao(self):
        """O que o estilo gera sem texto visivel nao tira o recorte da decoracao."""
        casos = [
            ("plantio-d-url", "#plantio-d-url-f::before{content:url(\"data:image/gif;base64,R0lGODlhAQABAAAAACw=\")}",
             'aria-hidden="true"', "", "imagem por url(), com aria-hidden"),
            ("plantio-d-quebra", "#plantio-d-quebra-f::before{content:'\\A';white-space:pre}",
             "", "", "so quebra de linha"),
            ("plantio-d-zw", "#plantio-d-zw-f::before{content:'\\200B'}",
             "", "", "so espaco de largura zero"),
            ("plantio-d-icone", "#plantio-d-icone-f::before{content:'\\e900'}",
             'aria-hidden="true"', "", "glifo de icone com aria-hidden"),
            ("plantio-d-vazio", "#plantio-d-vazio-f::after{content:'';display:table;clear:both}",
             "", "", "content vazio (clearfix)"),
            ("plantio-d-invis", "#plantio-d-invis-f::before{content:'Saldo de R$ 12,00';visibility:hidden}",
             "", "", "pseudo com visibility:hidden"),
            ("plantio-d-oculto", "#plantio-d-oculto-n{display:none}#plantio-d-oculto-n::before{content:'Saldo de R$ 12,00'}",
             "", '<span id="plantio-d-oculto-n"></span>', "texto gerado num descendente display:none"),
            ("plantio-d-alt", "#plantio-d-alt-f::before{content:'\\e900' / 'Saldo de R$ 12,00'}",
             'aria-hidden="true"', "", "icone com texto alternativo depois de /, com aria-hidden"),
            ("plantio-d-shy", "#plantio-d-shy-f::before{content:'\\AD\\200E'}",
             "", "", "so hifen invisivel e marca de direcao"),
        ]
        for ident, css, attrs, dentro, rotulo in casos:
            with self.subTest(caso=ident):
                self._plantio_gerado(ident, css, attrs, dentro)
                self._exigir_decorativo(ident, rotulo, "23")

    def test_11_conteudo_visualmente_oculto_nao_e_defeito(self):
        leitura = medir(self.page, PISO, LIMITE)
        sr = [s for s in self._seletores(leitura) if "sr-only" in s]
        print(f"  [11] conteudo visualmente oculto (sr-only) na moldura: "
              f"{len(sr)} achado(s) -- o recorte ali e a propria tecnica de "
              f"acessibilidade, nao defeito")
        self.assertEqual(sr, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
