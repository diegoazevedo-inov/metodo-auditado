"""
Aplicacao de fixture para os GUARDS 4-6.

Nao e um projeto real: e a superficie minima que exercita tudo que a spec
exige do trio de medicao -- moldura com ancoras semanticas, rotas publicas e
protegidas, sessao que expira e redireciona para a tela de autenticacao,
paginas de detalhe com identificador, e uma lista que RENDERIZA DIFERENTE
conforme a largura (a armadilha que faz a varredura escolher as fichas num
viewport fixo).

Credenciais por variavel de ambiente, nunca embutidas.
"""

from __future__ import annotations

import http.server
import os
import socketserver
import sys
import urllib.parse

USUARIO = os.environ.get("FIXTURE_USUARIO", "operador")
SENHA = os.environ.get("FIXTURE_SENHA", "senha-de-fixture")
COOKIE = "fixture_sessao"
TOKEN = "sessao-valida"

CSS = """
*{box-sizing:border-box}
body{margin:0;font:14px/1.5 system-ui,sans-serif;color:#111;background:#fff}
[data-ui-frame]{display:flex;flex-direction:column;min-height:100vh}
.app-header{border-bottom:1px solid #999;padding:8px}
/* barra de abas: nao cabe na largura do celular */
#nav-abas{white-space:nowrap;overflow:hidden;font-weight:600}
#nav-abas a{margin-right:18px;text-decoration:none;color:#123}
main{padding:12px;flex:1}
table{border-collapse:collapse;width:100%}
th,td{border:1px solid #bbb;padding:4px 8px;text-align:left}
.painel-rolavel{height:120px;border:1px solid #bbb}
/* utilitarios reconhecidos pela sonda por NOME de classe */
.truncate{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.overflow-x-auto{overflow-x:auto}
.overflow-y-auto{overflow-y:auto}
.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;
         clip-path:inset(50%);white-space:nowrap}
@media (min-width:768px){
  .md\\:truncate{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
}
/* no celular a tabela mostra so as tres primeiras linhas */
@media (max-width:767px){ tr.linha-extra{display:none} }
"""

CLIENTES = [
    ("c-1001", "Industria Meridional de Componentes Tecnicos"),
    ("c-1002", "Cooperativa Agropecuaria do Vale Central"),
    ("c-1003", "Transportadora Litoranea Reunida"),
    ("c-1004", "Construtora Pilar do Norte"),
    ("c-1005", "Laboratorio Analitico Bandeirantes"),
]


def moldura(titulo: str, conteudo: str) -> str:
    """
    Layout raiz. Declara os dois marcadores, independentes de estilo, que o
    GUARD 6 usa: `data-ui-frame` na moldura e `data-ui-content` na area de
    conteudo. E defeito de pagina o que esta sob o marcador de conteudo; o
    resto e estrutura compartilhada (ver DECISOES.md 2.2).
    """
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{titulo}</title><style>{CSS}</style></head>
<body>
<div data-ui-frame>
  <header class="app-header">
    <span class="sr-only">Navegacao principal do sistema de fixture</span>
    <nav id="nav-abas">
      <a href="/">Painel</a><a href="/clientes">Clientes</a>
      <a href="/relatorios">Relatorios</a><a href="/publico/precos">Precos</a>
      <a href="/clientes/c-1001">Ficha de exemplo</a><a href="/sair">Sair</a>
    </nav>
  </header>
  <main data-ui-content>{conteudo}</main>
</div>
</body></html>"""


def pagina_painel() -> str:
    return """
<h1>Painel</h1>
<div class="painel-rolavel overflow-y-auto">
  <p>Resumo do dia. Este painel rola na vertical quando o conteudo passa da altura.</p>
  <p>Os numeros vem do fechamento da noite anterior e sao atualizados de
     madrugada, uma vez por dia.</p>
</div>
<div class="overflow-x-auto" id="faixa-declarada">
  <div style="width:1400px">faixa com rolagem horizontal DECLARADA</div>
</div>
"""


def pagina_clientes() -> str:
    linhas = "".join(
        f'<tr class="{"linha-extra" if i >= 3 else ""}">'
        f'<td><a href="/clientes/{cid}">{cid}</a></td>'
        f'<td class="truncate" style="max-width:180px">{nome}</td></tr>'
        for i, (cid, nome) in enumerate(CLIENTES)
    )
    return f"""
<h1>Clientes</h1>
<table id="tabela-clientes"><thead><tr><th>Codigo</th><th>Razao social</th></tr></thead>
<tbody>{linhas}</tbody></table>
"""


def pagina_detalhe(cid: str) -> str:
    nome = dict(CLIENTES).get(cid)
    if nome is None:
        return None
    return f"""
<h1>Ficha do cliente</h1>
<p><strong>{cid}</strong></p>
<div id="razao-social-longa" class="md:truncate" style="white-space:nowrap">{nome} — filial matriz</div>
<p>Cadastro sem pendencias.</p>
"""


def pagina_relatorios() -> str:
    colunas = "".join(f"<th>Competencia {m:02d}/2026</th>" for m in range(1, 13))
    celulas = "".join(f"<td>R$ {m * 1234},00</td>" for m in range(1, 13))
    return f"""
<h1>Relatorios</h1>
<div id="bloco-relatorio">
  <table id="tabela-competencias"><thead><tr><th>Centro de custo</th>{colunas}</tr></thead>
  <tbody><tr><td>Administrativo</td>{celulas}</tr></tbody></table>
</div>
"""


def pagina_precos() -> str:
    return """
<h1>Precos</h1>
<p>Tabela de precos. Esta pagina nao exige login.</p>
<ul><li>Plano basico</li><li>Plano ampliado</li></ul>
"""


def pagina_login(erro: bool = False) -> str:
    aviso = '<p id="erro-login">Credenciais invalidas.</p>' if erro else ""
    return f"""
<h1 id="titulo-login">Autenticacao</h1>{aviso}
<form method="post" action="/login">
  <label>Usuario <input name="usuario"></label>
  <label>Senha <input name="senha" type="password"></label>
  <button type="submit">Entrar</button>
</form>
"""


ROTAS_PUBLICAS = {"/login", "/publico/precos"}


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _responder(self, corpo: str, status: int = 200, cabecalhos=()):
        dados = corpo.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.send_header("Cache-Control", "no-store")
        for k, v in cabecalhos:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(dados)

    def _tem_sessao(self) -> bool:
        return f"{COOKIE}={TOKEN}" in (self.headers.get("Cookie") or "")

    def do_GET(self):
        caminho = urllib.parse.urlparse(self.path).path.rstrip("/") or "/"

        if caminho == "/sair":
            self._responder("", 302, [("Location", "/login"),
                                      ("Set-Cookie", f"{COOKIE}=; Path=/; Max-Age=0")])
            return

        if caminho not in ROTAS_PUBLICAS and caminho != "/" and not self._tem_sessao():
            # sessao expirada redireciona para a tela de autenticacao: e por
            # isso que a varredura precisa validar o destino final
            self._responder("", 302, [("Location", "/login")])
            return
        if caminho == "/" and not self._tem_sessao():
            self._responder("", 302, [("Location", "/login")])
            return

        if caminho == "/login":
            self._responder(moldura("Entrar", pagina_login()))
        elif caminho == "/":
            self._responder(moldura("Painel", pagina_painel()))
        elif caminho == "/clientes":
            self._responder(moldura("Clientes", pagina_clientes()))
        elif caminho.startswith("/clientes/"):
            corpo = pagina_detalhe(caminho.rsplit("/", 1)[-1])
            if corpo is None:
                self._responder(moldura("Nao encontrado", "<h1>404</h1>"), 404)
            else:
                self._responder(moldura("Ficha", corpo))
        elif caminho == "/relatorios":
            self._responder(moldura("Relatorios", pagina_relatorios()))
        elif caminho in ("/erro/500", "/erro/503"):
            # Respondem erro de servidor na propria URL. So entram numa varredura
            # quando uma prova as poe na matriz (prova 6, etapa h).
            codigo = int(caminho.rsplit("/", 1)[-1])
            self._responder(moldura("Erro", f"<h1>{codigo}</h1>"), codigo)
        elif caminho == "/publico/precos":
            self._responder(moldura("Precos", pagina_precos()))
        else:
            self._responder(moldura("Nao encontrado", "<h1>404</h1>"), 404)

    def do_POST(self):
        tamanho = int(self.headers.get("Content-Length") or 0)
        campos = urllib.parse.parse_qs(self.rfile.read(tamanho).decode("utf-8"))
        ok = (campos.get("usuario", [""])[0] == USUARIO
              and campos.get("senha", [""])[0] == SENHA)
        if ok:
            self._responder("", 302, [("Location", "/"),
                                      ("Set-Cookie", f"{COOKIE}={TOKEN}; Path=/")])
        else:
            self._responder(moldura("Entrar", pagina_login(erro=True)), 401)


class Servidor(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else 8731
    with Servidor(("127.0.0.1", porta), Handler) as srv:
        print(f"fixture em http://127.0.0.1:{porta}", flush=True)
        srv.serve_forever()
