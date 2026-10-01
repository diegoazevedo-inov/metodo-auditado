"""
GUARD 6 -- Consolidacao e assinatura.

Junta os parciais gravados pela varredura, produz o relatorio e -- o ponto
central -- produz a PROVA DE REPRODUTIBILIDADE da medicao.

CODIGOS DE SAIDA:
    0 -> consolidei: relatorio, assinatura e resumos criptograficos gravados
    2 -> RECUSO: parcial ausente, mistura de execucoes, mistura de ESCOPOS
         (inclusive as rotas medidas e as fichas de detalhe), identificador
         ausente (vazio ou o rotulo de ausencia que a varredura grava),
         nenhum viewport ou nenhuma rota nos parciais (escopo vazio nao e
         base limpa), ou ancora obsoleta com defeitos presentes
Este guard nao devolve 1: encontrar defeito nao e reprovar, e a materia-prima
da baseline. O veredito de "piorou" pertence a comparacao entre assinaturas.

LIMITACOES DECLARADAS -- o que este guard NAO cobre:
  * A assinatura cobre apenas DEFEITOS DE PAGINA, como a spec determina. Um
    defeito que exista somente na moldura nao altera a assinatura: ele aparece
    no relatorio e conta como item de trabalho, mas uma regressao restrita a
    moldura passa despercebida pela prova de reprodutibilidade. Quem vigia a
    moldura e o relatorio, nao a assinatura.
  * A assinatura ignora MAGNITUDES por decisao explicita. Um defeito que
    piora de 10px para 900px, sem mudar de seletor nem de especie, produz
    assinatura identica.
  * A classificacao depende so do marcador de conteudo: achado sob ele e de
    PAGINA, o resto e moldura. O guard de ancora recusa (2) apenas marcador
    que nao casa NENHUM defeito na execucao inteira. Uma rota renderizada sem
    o marcador de conteudo -- num layout proprio, por exemplo -- tem todos os
    defeitos contados como moldura, sai como saudavel e fica fora da
    assinatura, sem recusa; um marcador posto em outro lugar que ainda case
    algum defeito tambem passa.
  * A assinatura e um CONJUNTO. Dois defeitos com o mesmo seletor legivel, na
    mesma rota, viewport e especie, viram uma linha so: corrigir um e deixar
    o outro nao muda a assinatura.
  * Nao le assinatura anterior nenhuma, e nada no kit compara a assinatura
    corrente com uma fixada: a comparacao entre execucoes e passo manual (a
    prova 6 usa `diff`). O "piorou" de que fala o codigo de saida nao tem
    gate que o aplique.
  * O seletor vem da sonda e e legivel, nao canonico. Uma remontagem de DOM
    que mude o caminho legivel muda a assinatura sem que o defeito tenha
    mudado, e isso aparece como falsa divergencia entre execucoes.
  * Consolida o que os parciais trazem. Nao revisita a aplicacao, nao
    reconfere nada e nao sabe se a varredura mediu o estado certo.
  * PRE-CONDICAO DO ARRANJO DE ANCORAS: o guard de ancora exige que as DUAS
    ancoras casem defeito. Isso funciona em layout onde a area de conteudo e
    descendente da moldura, que e o caso comum -- todo defeito de conteudo
    casa as duas. Em layout onde as ancoras sejam IRMAS, uma aplicacao sem
    nenhum defeito de moldura passaria a ser recusada com 2, acusando estado
    legitimo. Quem adotar o kit com outro arranjo precisa rever esta regra.
  * Uma rota com `nao_medivel` no parcial (a varredura grava assim a rota
    cuja resposta principal teve status 4xx ou 5xx) entra na contagem de
    quebradas e e listada com o motivo no relatorio, mas NAO entra na
    assinatura, que so traz defeitos de pagina. Uma rota sem nenhum estouro
    que passe a responder erro muda o relatorio e deixa a assinatura igual.
  * O identificador da execucao fica SO nos parciais. Relatorio, assinatura e
    `resumos.sha256` nao o carregam, e por isso saem iguais byte a byte em duas
    execucoes independentes de uma interface que nao mudou; o resumo cobre
    exatamente o relatorio e a assinatura. Os parciais, que carregam o
    identificador, ficam FORA do resumo: `sha256sum -c` nao confere a
    integridade deles, e um parcial alterado depois da consolidacao so e
    notado se a consolidacao for refeita.
  * A recusa de mistura compara identificador e escopo. Dois parciais de
    execucoes diferentes, com o MESMO identificador e o mesmo escopo (mesma
    configuracao e mesmas rotas), passam como uma execucao so. Por isso o
    identificador precisa ser unico de verdade -- o hash do commit, que se
    repete a cada execucao do mesmo commit, nao serve.
  * Consolidacao recusada (saida 2) nao apaga o relatorio, a assinatura e o
    resumo de uma consolidacao anterior no mesmo diretorio, e eles continuam
    fechando em `sha256sum -c`. Vale o codigo de saida da execucao atual: o
    diretorio sozinho nao diz se a ultima consolidacao foi aceita.
  RECURSO COMPLEMENTAR para o que fica descoberto: so dar a baseline por fixada
  depois que DUAS execucoes independentes tiverem assinatura identica.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from .common import (
    EXIT_CLEAN, GuardCannotRun, load_config, optional, require, run_guard,
)

RAIZ_KIT = Path(__file__).resolve().parent.parent

SENTINELA_ID = "SEM-IDENTIFICADOR"


def modulo_da_rota(rota: str) -> str:
    """
    DECISAO DE PROJETO -- 'modulo' e o primeiro segmento do caminho.
    E derivavel da propria rota, deterministico, e agrupa a lista e as fichas
    de um mesmo assunto no mesmo item de trabalho.
    """
    partes = [p for p in rota.split("/") if p]
    return partes[0] if partes else "(raiz)"


class Consolidador:
    def __init__(self, diretorio: Path, viewports_esperados: list[str], ancoras: dict):
        if not viewports_esperados:
            raise GuardCannotRun(
                "a matriz nao declara nenhum viewport: nada a consolidar, e escopo "
                "vazio nao e base limpa")
        self.dir = diretorio
        self.esperados = sorted(viewports_esperados)
        self.ancoras = ancoras
        self.parciais: dict[str, dict] = {}

    # -- recusas -----------------------------------------------------------
    def carregar(self):
        if not self.dir.is_dir():
            raise GuardCannotRun(
                f"diretorio de parciais nao existe: {self.dir}\n"
                f"  para produzi-lo: {comando_varredura(self.dir)}")
        faltando = []
        for nome in self.esperados:
            caminho = self.dir / f"parcial-{nome}.json"
            if not caminho.is_file():
                faltando.append(caminho.name)
                continue
            try:
                bruto = caminho.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                raise GuardCannotRun(f"parcial ilegivel {caminho.name}: {exc}") from exc
            try:
                self.parciais[nome] = json.loads(bruto)
            except json.JSONDecodeError as exc:
                raise GuardCannotRun(f"parcial malformado {caminho.name}: {exc}") from exc
        if faltando:
            raise GuardCannotRun(
                f"parcial(is) esperado(s) ausente(s): {', '.join(faltando)}. "
                "Sem todos os viewports nao ha baseline, e nenhum relatorio e gerado.\n"
                f"  para produzir os que faltam: {comando_varredura(self.dir)}")

        ids = {nome: p.get("identificador_execucao") for nome, p in self.parciais.items()}
        vazios = sorted(n for n, i in ids.items() if not i or i == SENTINELA_ID)
        if vazios:
            raise GuardCannotRun(
                f"identificador de execucao ausente em: {', '.join(vazios)} "
                "(vazio ou o rotulo de ausencia gravado pela varredura). Sem "
                "identificador nao ha como saber se os parciais vem da mesma rodada, "
                "e a recusa por identificadores diferentes deixaria a mistura passar.\n"
                f"  informe um identificador: {comando_varredura(self.dir)}")
        distintos = sorted(set(ids.values()))
        if len(distintos) > 1:
            detalhe = "; ".join(f"{n}={i}" for n, i in sorted(ids.items()))
            raise GuardCannotRun(
                f"os parciais declaram identificadores de execucao DIFERENTES "
                f"({', '.join(distintos)}): {detalhe}. Junta-los produziria um "
                "relatorio de uma execucao que nao existiu.")
        self.id_execucao = distintos[0]
        self._conferir_escopo()

    # Campos do escopo que descrevem a CONFIGURACAO da medicao, iguais em
    # todos os viewports por construcao. O que varia legitimamente de um
    # viewport para outro (o proprio viewport) fica de fora.
    # As rotas medidas e as fichas de detalhe tambem: numa mesma execucao
    # todos os viewports percorrem a mesma lista, e sem conferi-las dois
    # parciais com o mesmo identificador e matrizes diferentes se juntavam.
    CAMPOS_DE_ESCOPO = ("piso_severidade_px", "ancoras", "areas",
                        "viewport_de_resolucao_de_detalhe", "fora_de_escopo",
                        "rotas_medidas", "identificadores_de_detalhe")

    def _conferir_escopo(self):
        """
        RECUSA parciais medidos com escopos diferentes.

        O relatorio imprime UM escopo. Lendo-o do primeiro parcial em ordem
        alfabetica e calando sobre o resto, dois parciais com pisos diferentes
        -- ou com ancoras diferentes -- viravam um relatorio que descreve uma
        medicao que nao aconteceu. Recusar mistura de execucao e nao recusar
        mistura de escopo deixa a metade silenciosa da mesma porta aberta.
        """
        divergentes = []
        referencia_nome = self.esperados[0]
        referencia = self.parciais[referencia_nome].get("escopo_aplicado", {})
        for nome in self.esperados[1:]:
            escopo = self.parciais[nome].get("escopo_aplicado", {})
            for campo in self.CAMPOS_DE_ESCOPO:
                if escopo.get(campo) != referencia.get(campo):
                    divergentes.append(
                        f"{campo}: {referencia_nome}={referencia.get(campo)!r} "
                        f"!= {nome}={escopo.get(campo)!r}")
        if divergentes:
            raise GuardCannotRun(
                "os parciais foram medidos com ESCOPOS diferentes:\n  "
                + "\n  ".join(divergentes)
                + "\nO relatorio imprime um escopo so; junta-los descreveria uma "
                "medicao que nao aconteceu. Rode os viewports com a mesma "
                "configuracao.")

    # -- classificacao -----------------------------------------------------
    def separar(self):
        """
        Separa defeito de ESTRUTURA COMPARTILHADA de defeito de PAGINA.

        Um estouro na moldura aparece de novo em toda rota que a desenha.
        Contado junto com os de pagina, o mesmo conserto entraria uma vez por
        rota, e o ranking passaria a medir a moldura em vez das paginas.

        REGRA (mecanismo desta implementacao, ver DECISOES.md 2.2): o layout
        raiz declara dois marcadores independentes de estilo, um na moldura e
        outro na area de conteudo. E defeito de PAGINA o que esta sob o
        marcador de conteudo; todo o resto e estrutura compartilhada --
        inclusive <html> e <body>, a casca do documento, que nao esta sob
        marcador nenhum. Classificar essa casca como pagina produziria a
        inflacao que a separacao existe para evitar, porque ela reaparece em
        toda rota que tenha qualquer estouro.
        """
        self.moldura: list[tuple] = []
        self.pagina: list[tuple] = []
        self.acionaveis: list[tuple] = []
        self.casou_moldura = 0
        self.casou_conteudo = 0
        self.instaveis = 0
        self.rotas_quebradas: set[tuple[str, str]] = set()
        self.rotas_totais: set[tuple[str, str]] = set()
        self.nao_mediveis: set[tuple[str, str]] = set()

        self.motivos_nao_medivel: dict[tuple[str, str], str] = {}
        for nome in self.esperados:
            parcial = self.parciais[nome]
            self.instaveis += int(parcial.get("instaveis", 0))
            for reg in parcial["registros"]:
                rota = reg["rota"]
                self.rotas_totais.add((nome, rota))
                if reg.get("nao_medivel"):
                    # rota que nao pode ser medida vai para as QUEBRADAS
                    self.nao_mediveis.add((nome, rota))
                    self.rotas_quebradas.add((nome, rota))
                    self.motivos_nao_medivel[(nome, rota)] = str(
                        reg.get("motivo_nao_medivel", "(sem motivo registrado)"))
                    continue
                for a in reg["achados"]:
                    if not a["no_placar"]:
                        continue
                    if a.get("sob_ancora_moldura"):
                        self.casou_moldura += 1
                    if a.get("sob_ancora_conteudo"):
                        self.casou_conteudo += 1
                    chave = (nome, rota, a["especie"], a["seletor"])
                    if a.get("sob_ancora_conteudo"):
                        self.pagina.append(chave)
                        self.acionaveis.append(
                            (*chave, bool(a.get("tem_achado_mais_interno"))))
                        self.rotas_quebradas.add((nome, rota))
                    else:
                        self.moldura.append(chave)
        if not self.rotas_totais:
            raise GuardCannotRun(
                "os parciais nao trazem nenhuma rota: a execucao mediu nada, e escopo "
                "vazio nao e base limpa. Uma assinatura vazia aqui nao provaria nada.")

    def guarda_de_ancora(self) -> str:
        """
        Havendo defeitos, recusa se QUALQUER marcador nao corresponder a
        nenhum deles: e o que acontece quando um marcador e renomeado ou sai
        do layout, e sem esta recusa a classificacao sairia errada sem aviso.

        Com o PLACAR ZERO a verificacao NAO E APLICADA, e o consolidador AVISA:
        sem defeitos nao ha nada para os marcadores separarem, e a assinatura
        vazia e o esperado de uma aplicacao sem estouro. Isso nao esconde
        defeito: os marcadores so decidem de que lado cada achado fica, nunca
        se ele e achado.
        """
        total = len(self.moldura) + len(self.pagina)
        if total == 0:
            return ("AVISO: placar zero -- guarda de ancora NAO APLICADO. Sem defeitos "
                    "nao ha nada para as ancoras separarem, e a assinatura vazia e o "
                    "esperado. Isso nao esconde defeito: a ancora so decide de que lado "
                    "cada achado fica, nunca se ele e achado.")
        mudas = []
        if self.casou_moldura == 0:
            mudas.append(f"moldura ({self.ancoras.get('moldura')!r})")
        if self.casou_conteudo == 0:
            mudas.append(f"conteudo ({self.ancoras.get('conteudo')!r})")
        if mudas:
            raise GuardCannotRun(
                f"ANCORA OBSOLETA: a(s) ancora(s) {', '.join(mudas)} casou(aram) ZERO "
                f"dos {total} defeitos do placar. Com uma ancora renomeada, a "
                "separacao moldura/pagina sairia errada sem que nada acusasse, e o "
                "ranking deixaria de apontar o trabalho certo.\n"
                "  confira o seletor em [medicao.ancoras] no guards.toml contra o "
                "layout raiz da aplicacao.")
        return (f"guarda de ancora OK: moldura casou {self.casou_moldura} defeito(s), "
                f"conteudo casou {self.casou_conteudo}.")

    # -- saidas ------------------------------------------------------------
    def assinatura(self) -> str:
        """
        Duas execucoes sao confrontadas pela ASSINATURA: uma linha por
        defeito de PAGINA -- viewport, rota, especie, seletor -- em ordem.

        Fica de fora tudo o que varia sem que a interface mude: excedente em
        pixels, data e hora, texto lido da tela (um nome de cliente, uma data
        de vencimento). O que tem de se repetir e a LISTA de defeitos.
        """
        return "".join(f"{v}\t{r}\t{e}\t{s}\n"
                       for v, r, e, s in sorted(set(self.pagina)))

    def relatorio(self, aviso_ancora: str) -> str:
        L = [
            "RELATORIO DE ESTOURO HORIZONTAL",
            "=" * 70,
            f"viewports consolidados    : {', '.join(self.esperados)}",
            f"ancoras                   : moldura={self.ancoras.get('moldura')} "
            f"conteudo={self.ancoras.get('conteudo')}",
            "",
            "-- PLACAR --",
            f"  medicoes de rota            : {len(self.rotas_totais)}",
            f"  rotas quebradas             : {len(self.rotas_quebradas)}",
            f"  rotas saudaveis             : {len(self.rotas_totais) - len(self.rotas_quebradas)}",
            f"  rotas NAO MEDIVEIS          : {len(self.nao_mediveis)}  "
            "(ja incluidas nas quebradas)",
            f"  registros INSTAVEIS         : {self.instaveis}  "
            "(leituras que nao se repetiram dentro da janela)",
            f"  defeitos de pagina          : {len(self.pagina)} "
            f"({len(set(self.pagina))} distintos)",
            f"  defeitos da moldura         : {len(self.moldura)} "
            f"({len(set((e, s) for _v, _r, e, s in self.moldura))} itens de trabalho)",
            "",
            aviso_ancora,
            "",
            "-- ROTAS NAO MEDIVEIS (contadas como quebradas) --",
        ]
        if not self.motivos_nao_medivel:
            L.append("  (nenhuma)")
        for (v, r), motivo in sorted(self.motivos_nao_medivel.items()):
            L.append(f"    [{v}] {r}: {motivo}")
        L += [
            "",
            "-- ESTRUTURA COMPARTILHADA (MOLDURA) --",
            "  Cada estouro da moldura aparece aqui uma vez; ele nao torna rota",
            "  nenhuma quebrada e nao entra no ranking.",
        ]
        agreg = defaultdict(set)
        for v, r, e, s in self.moldura:
            agreg[(e, s)].add(v)
        if not agreg:
            L.append("  (nenhum)")
        for (e, s), vps in sorted(agreg.items()):
            L.append(f"    [{e}] {s}")
            L.append(f"      1 item de trabalho, visto em {len(vps)} viewport(s): "
                     f"{', '.join(sorted(vps))}")

        L += ["", "-- RANKING POR MODULO (apenas defeitos de pagina) --",
              "  A moldura tem secao propria acima; aqui entram so as paginas."]
        por_modulo = Counter(modulo_da_rota(r) for _v, r, _e, _s in self.pagina)
        rotas_por_modulo = defaultdict(set)
        for v, r, _e, _s in self.pagina:
            rotas_por_modulo[modulo_da_rota(r)].add(r)
        if not por_modulo:
            L.append("  (nenhum)")
        for mod, n in sorted(por_modulo.items(), key=lambda kv: (-kv[1], kv[0])):
            L.append(f"    {n:4d} defeito(s)  modulo '{mod}'  "
                     f"em {len(rotas_por_modulo[mod])} rota(s)")

        L += ["", "-- PONTOS ACIONAVEIS (defeitos de pagina sem achado mais interno) --",
              "  Quando varios elementos aninhados acusam o mesmo excesso, lista so",
              "  os que nao tem outro achado dentro de si: e por eles que se comeca."]
        fundo = sorted({(r, e, s_) for _v, r, e, s_, interno in self.acionaveis
                        if not interno})
        if not fundo:
            L.append("  (nenhum)")
        for r, e, s_ in fundo:
            vps = sorted({v for v, rr, ee, ss, _i in self.acionaveis
                          if (rr, ee, ss) == (r, e, s_)})
            L.append(f"    {r:24} {e:22} {s_}   [{', '.join(vps)}]")

        L += ["", "-- DEFEITOS DE PAGINA, POR VIEWPORT --"]
        por_vp = defaultdict(list)
        for v, r, e, s in self.pagina:
            por_vp[v].append((r, e, s))
        for vp in self.esperados:
            itens = sorted(set(por_vp.get(vp, [])))
            L.append(f"  [{vp}] {len(itens)} defeito(s)")
            for r, e, s in itens:
                L.append(f"      {r:24} {e:22} {s}")

        L += ["", "-- ESCOPO --"]
        # Seguro: `carregar` ja recusou parciais de escopos divergentes.
        escopo = self.parciais[self.esperados[0]]["escopo_aplicado"]
        L.append(f"  piso de severidade: {escopo.get('piso_severidade_px')}px")
        L.append("  identificadores de detalhe resolvidos no viewport: "
                 f"{escopo.get('viewport_de_resolucao_de_detalhe')}")
        L.append("  rotas excluidas da medicao, com o motivo:")
        for f in escopo.get("fora_de_escopo", []):
            L.append(f"    {f['rota']}: {f['motivo']}")
        L.append("")
        L.append("-- ASSINATURA --")
        L.append(f"  {len(set(self.pagina))} tupla(s) (viewport, rota, especie, seletor)")
        L.append("  sem excedente em pixels, sem data ou hora, sem texto lido da tela.")
        L.append("  A baseline vale como fixada depois que duas execucoes independentes")
        L.append("  produzirem esta mesma assinatura.")
        return "\n".join(L) + "\n"

    def gravar(self, aviso: str) -> list[Path]:
        rel = self.dir / "relatorio.txt"
        ass = self.dir / "assinatura.txt"
        rel.write_text(self.relatorio(aviso), encoding="utf-8")
        ass.write_text(self.assinatura(), encoding="utf-8")
        # O resumo e calculado sobre os bytes que acabaram de ser gravados, no
        # formato de linha do sha256sum: `sha256sum -c` confere sem ajuste.
        # Cobre so relatorio e assinatura, que nao carregam o identificador e
        # por isso se repetem entre execucoes; os parciais carregam, e ficam fora.
        linhas = []
        for caminho in sorted([rel, ass]):
            h = hashlib.sha256(caminho.read_bytes()).hexdigest()
            linhas.append(f"{h}  {caminho.name}\n")
        resumos = self.dir / "resumos.sha256"
        resumos.write_text("".join(linhas), encoding="utf-8")
        return [rel, ass, resumos]


def comando_varredura(saida: Path) -> str:
    """Comando que produz parciais em `saida`, valido de qualquer diretorio."""
    return (f"cd {RAIZ_KIT} && python3 sweep/executar.py "
            f"--id \"$(python3 -c 'import uuid; print(uuid.uuid4())')\" --saida {saida}")


def main() -> int:
    ap = argparse.ArgumentParser(description="GUARD 6 -- consolidacao e assinatura")
    ap.add_argument("--config", default="guards.toml")
    ap.add_argument("--rotas", default="rotas.toml")
    # O padrao e o diretorio de medicao nova, o mesmo da varredura; a
    # baseline fixada (out/varredura) so e consolidada quando se pede.
    ap.add_argument("--parciais", default="out/medicao")
    args = ap.parse_args()

    cfg_path = Path(args.config).resolve()
    cfg = load_config(cfg_path)
    rotas = load_config(Path(args.rotas).resolve())
    med = require(cfg, "medicao", "raiz", "tabela")
    ancoras = optional(med, "ancoras", "medicao", "tabela de textos", {})
    viewports = [require(v, "nome", f"viewport #{i + 1}", "texto")
                 for i, v in enumerate(require(rotas, "viewport", "rotas", "lista de tabelas"))]

    c = Consolidador(Path(args.parciais).resolve(), viewports, ancoras)
    c.carregar()
    c.separar()
    aviso = c.guarda_de_ancora()
    escritos = c.gravar(aviso)

    print(c.relatorio(aviso))
    print("gravados:")
    for p in escritos:
        print(f"  {p}")
    print(f"\nconferencia com a ferramenta padrao do sistema:")
    print(f"  cd {c.dir} && sha256sum -c resumos.sha256")
    return EXIT_CLEAN


if __name__ == "__main__":
    run_guard(main)
