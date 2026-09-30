"""
Ponto de entrada da suite de medicao (GUARD 5).

Esta suite comeca pela prova do detector (GUARD 4). Se ela reprovar, a
varredura nem comeca e NENHUM PARCIAL e gravado.

CODIGOS DE SAIDA:
    0 -> a suite passou E os parciais esperados estao no disco
    1 -> a varredura falhou nas tres condicoes que ela sabe julgar: destino
         divergente, cobertura de detalhe encolhida, ou estado inicial nao
         aplicado. Sao as tres que chegam como FALHA de assercao; qualquer
         outra excecao e erro de execucao e sai 2 (ver abaixo)
    2 -> nao consigo executar: credenciais ausentes OU RECUSADAS, navegador
         ausente, aplicacao fora do ar, configuracao invalida, A PROVA DO
         DETECTOR FALHOU, ou a suite terminou sem produzir a medicao completa
         (teste pulado, parcial faltando). Com o instrumento reprovado ou a
         medicao incompleta nao existe baseline valida a produzir, entao isto
         nunca vira 1 -- e muito menos 0.

Nao existe opcao de pular a prova do detector: uma garantia com chave por
fora nao e garantia.
"""

from __future__ import annotations

import argparse
import os
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from uiguards.common import EXIT_CANNOT_RUN, EXIT_CLEAN, EXIT_VIOLATION  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="GUARD 5 -- varredura multi-viewport")
    ap.add_argument("--id", help="identificador unico da execucao (ou VARREDURA_ID)")
    ap.add_argument("--saida", help="diretorio de saida dos parciais (ou VARREDURA_SAIDA)")
    ap.add_argument("--base-url", help="URL base da aplicacao (ou FIXTURE_BASE_URL)")
    ap.add_argument("--rotas", help="arquivo da matriz de rotas (padrao rotas.toml)")
    args = ap.parse_args()
    # NAO existe opcao de pular a prova do detector. Havia uma, oculta do
    # --help, e ela desligava em silencio a garantia central desta suite --
    # medir so depois que o detector passou pela prova -- deixando
    # parciais indistinguiveis dos legitimos, que o GUARD 6 assinava sem
    # perceber. Uma garantia com chave por fora nao e garantia. A prova de
    # que a barreira funciona esta em proofs/prova_guard5.sh (d), que sabota
    # a sonda de verdade em vez de contornar a barreira.

    if args.id:
        os.environ["VARREDURA_ID"] = args.id
    if args.saida:
        os.environ["VARREDURA_SAIDA"] = str(Path(args.saida).resolve())
    if args.base_url:
        os.environ["FIXTURE_BASE_URL"] = args.base_url
    if args.rotas:
        os.environ["VARREDURA_ROTAS"] = args.rotas

    # ENTRADA AUSENTE E 2, ANTES DE QUALQUER COISA. As credenciais sao entrada
    # declarada desta suite; sem elas nao ha medicao a produzir. Conferir aqui,
    # e nao dentro do teste, e o que impede que `unittest` transforme a falta
    # em teste PULADO -- que ele conta como sucesso, e a suite sairia com 0
    # tendo medido zero rota.
    from uiguards.common import GuardCannotRun
    try:
        # Importar o modulo ja confere a configuracao (tipos, matriz vazia).
        from sweep.varredura import credenciais
        credenciais()
    except GuardCannotRun as exc:
        print(f"NAO CONSIGO EXECUTAR: {exc}", file=sys.stderr)
        return EXIT_CANNOT_RUN

    carregador = unittest.TestLoader()

    print("=" * 70)
    print("ETAPA 1/2 -- PROVA DO DETECTOR (GUARD 4)")
    print("a varredura so comeca se esta prova passar")
    print("=" * 70)
    from sweep import prova_sonda
    r = unittest.TextTestRunner(verbosity=2).run(
        carregador.loadTestsFromModule(prova_sonda))
    if not r.wasSuccessful():
        if r.errors and not r.failures:
            # O instrumento nao foi julgado: a prova nem chegou a medir.
            # Dizer "o instrumento esta quebrado" quando o que falta e o
            # servidor manda quem investiga para o lugar errado.
            print("\nA PROVA DO DETECTOR NAO CHEGOU A RODAR: erro de execucao "
                  "(aplicacao fora do ar, navegador ausente). O instrumento "
                  "nao foi julgado.", file=sys.stderr)
        else:
            print("\nPROVA DO DETECTOR REPROVADA: o instrumento esta quebrado.",
                  file=sys.stderr)
        print("NAO CONSIGO EXECUTAR: sem detector provado nao ha medicao "
              "valida a produzir; nenhum parcial foi gravado.", file=sys.stderr)
        return EXIT_CANNOT_RUN

    print()
    print("=" * 70)
    print("ETAPA 2/2 -- VARREDURA MULTI-VIEWPORT (GUARD 5)")
    print(f"identificador da execucao: {os.environ.get('VARREDURA_ID', '(ausente)')}")
    print("=" * 70)
    from sweep import varredura
    r = unittest.TextTestRunner(verbosity=2).run(
        carregador.loadTestsFromTestCase(varredura.VarreduraBase))
    # ERRO DE EXECUCAO NAO E VIOLACAO. As tres condicoes que a varredura sabe
    # julgar chegam aqui como FALHA de assercao. Qualquer outra excecao --
    # credencial recusada, aplicacao fora do ar, navegador morto, erro de
    # preparacao -- significa que nenhuma medicao foi produzida: e 2. Devolver
    # 1 ali faz um problema de infraestrutura passar por divida de layout, e
    # uma senha rotacionada vira "violacao" no CI.
    if r.errors:
        print("\nNAO CONSIGO EXECUTAR: a varredura parou por ERRO DE EXECUCAO, "
              "nao por violacao. Nenhuma medicao foi produzida.", file=sys.stderr)
        for caso, _tb in r.errors:
            print(f"  erro em: {caso}", file=sys.stderr)
        return EXIT_CANNOT_RUN
    if r.failures:
        print("\nVARREDURA REPROVADA. Ela nao falha por encontrar defeitos -- "
              "encontra-los e a funcao dela.", file=sys.stderr)
        return EXIT_VIOLATION

    # NAO ANUNCIAR O QUE NAO ACONTECEU. `unittest` conta teste PULADO como
    # sucesso; um viewport pulado sairia daqui como suite verde e a linha
    # "parciais gravados" seria mentira. Confere-se o que existe no disco.
    esperados = [f"parcial-{vp['nome']}.json" for vp in varredura.ROTAS["viewport"]]
    faltando = [n for n in esperados if not (varredura.SAIDA / n).is_file()]
    if r.skipped or faltando:
        if r.skipped:
            print("\nTESTE(S) PULADO(S):", file=sys.stderr)
            for caso, motivo in r.skipped:
                print(f"  {caso}: {motivo}", file=sys.stderr)
        if faltando:
            print(f"\nparcial(is) nao gravado(s): {', '.join(faltando)}",
                  file=sys.stderr)
        print("NAO CONSIGO EXECUTAR: a suite terminou sem produzir a medicao "
              "completa. Suite verde sobre medicao incompleta e o modo de falha "
              "que o contrato comum existe para impedir.", file=sys.stderr)
        return EXIT_CANNOT_RUN

    print(f"\nparciais gravados em {varredura.SAIDA}: {', '.join(esperados)}")
    return EXIT_CLEAN


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print(f"NAO CONSIGO EXECUTAR: {exc!r}", file=sys.stderr)
        sys.exit(EXIT_CANNOT_RUN)
