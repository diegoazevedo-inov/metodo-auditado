"""
Determinacao do PISO DE SEVERIDADE por medicao (GUARD 4, ponto OPCIONAL).

A spec exige que o piso EXISTA e seja justificado por medicao; o valor
numerico e decisao de projeto. Este experimento faz o que a spec manda:
duas execucoes completas com piso ZERO, comparando o que entra e sai.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from playwright.sync_api import sync_playwright
from uiguards.overflow import medir, assentar

BASE = "http://127.0.0.1:8731"
ROTAS = ["/", "/clientes", "/relatorios", "/publico/precos", "/login",
         "/clientes/c-1001", "/clientes/c-1004"]
VIEWPORTS = [(320, 720), (390, 844), (768, 1024), (1280, 800), (1920, 1080)]


def execucao(pw):
    nav = pw.chromium.launch()
    ctx = nav.new_context(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
    pg = ctx.new_page()
    pg.goto(f"{BASE}/login", wait_until="domcontentloaded")
    pg.fill("input[name=usuario]", os.environ["FIXTURE_USUARIO"])
    pg.fill("input[name=senha]", os.environ["FIXTURE_SENHA"])
    pg.click("button[type=submit]")
    pg.wait_for_url(f"{BASE}/")
    out = {}
    for w, h in VIEWPORTS:
        pg.set_viewport_size({"width": w, "height": h})
        for rota in ROTAS:
            pg.goto(BASE + rota, wait_until="domcontentloaded")
            assentar(pg)
            leitura = medir(pg, 0.0, 500)   # PISO ZERO: ve tudo
            for nome, grupo in leitura["especies"].items():
                for a in grupo:
                    out[(w, rota, nome, a["seletor"])] = a["excedente"]
    nav.close()
    return out


with sync_playwright() as pw:
    a = execucao(pw)
    b = execucao(pw)

so_em_a = set(a) - set(b)
so_em_b = set(b) - set(a)
comuns = set(a) & set(b)
deltas = sorted(((abs(a[k] - b[k]), k) for k in comuns), reverse=True)

print(f"achados com piso ZERO: execucao A = {len(a)}, execucao B = {len(b)}")
print(f"instaveis (entram e saem entre execucoes): {len(so_em_a | so_em_b)}")
for k in sorted(so_em_a | so_em_b, key=str):
    v = a.get(k, b.get(k))
    print(f"    excedente {v:8.2f}px  vp{k[0]} {k[1]} {k[2]} {k[3]}")
print(f"\nmaiores oscilacoes de magnitude entre as duas execucoes:")
for d, k in deltas[:8]:
    print(f"    delta {d:6.2f}px  ({a[k]:.2f} -> {b[k]:.2f})  vp{k[0]} {k[1]} {k[3]}")
print("\ndistribuicao dos excedentes (execucao A):")
vals = sorted(a.values())
for lim in (0.5, 1, 2, 3, 5, 10, 50):
    print(f"    excedente < {lim:5}px : {sum(1 for v in vals if v < lim):3d} de {len(vals)}")
