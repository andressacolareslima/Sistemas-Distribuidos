import argparse
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
import sqlite3
from urllib.parse import parse_qsl, urlencode, urlsplit


class ErroHTTP(Exception):
    def __init__(self, status, mensagem):
        super().__init__(mensagem)
        self.status = status


class Fila:
    def __init__(self, arquivo):
        self.arquivo = arquivo
        with closing(self.conectar()) as banco, banco:
            banco.execute("PRAGMA journal_mode = WAL")
            banco.execute("""
                CREATE TABLE IF NOT EXISTS pedidos (
                    sequencia INTEGER PRIMARY KEY,
                    id TEXT NOT NULL UNIQUE,
                    dados TEXT NOT NULL,
                    resultado TEXT
                )
            """)
            banco.execute("""
                CREATE INDEX IF NOT EXISTS pedidos_pendentes ON pedidos(sequencia)
                WHERE resultado IS NULL
            """)

    def conectar(self):
        banco = sqlite3.connect(self.arquivo, timeout=3)
        banco.row_factory = sqlite3.Row
        banco.execute("PRAGMA synchronous = FULL")
        return banco

    def publicar(self, id_pedido, campos):
        dados = json.dumps(campos, sort_keys=True)
        with closing(self.conectar()) as banco, banco:
            banco.execute(
                "INSERT INTO pedidos (id, dados) VALUES (?, ?) ON CONFLICT(id) DO NOTHING",
                (id_pedido, dados),
            )
            pedido = banco.execute("SELECT * FROM pedidos WHERE id = ?", (id_pedido,)).fetchone()
            if pedido["dados"] != dados:
                raise ErroHTTP(409, "ID já usado com dados diferentes")
            return self.situacao(pedido)

    def consultar(self, id_pedido):
        with closing(self.conectar()) as banco:
            pedido = banco.execute("SELECT * FROM pedidos WHERE id = ?", (id_pedido,)).fetchone()
        if pedido is None:
            raise ErroHTTP(404, "Pedido inexistente")
        return self.situacao(pedido)

    def proximo(self, cursor):
        with closing(self.conectar()) as banco:
            return banco.execute(
                "SELECT * FROM pedidos WHERE sequencia > ? ORDER BY sequencia LIMIT 1", (cursor,)
            ).fetchone()

    def concluir(self, id_pedido, resultado):
        with closing(self.conectar()) as banco, banco:
            consulta = banco.execute("""
                UPDATE pedidos SET resultado = ?
                WHERE id = ? AND sequencia = (
                    SELECT MIN(sequencia) FROM pedidos WHERE resultado IS NULL
                )
            """, (json.dumps(resultado), id_pedido))
            if consulta.rowcount != 1:
                raise ErroHTTP(409, "O pedido já foi finalizado ou não é o primeiro pendente")

    @staticmethod
    def situacao(pedido):
        resultado = pedido["resultado"]
        return {
            "id": pedido["id"],
            "estado": "pendente" if resultado is None else "finalizado",
            "resultado": None if resultado is None else json.loads(resultado),
        }


class API(BaseHTTPRequestHandler):
    def do_GET(self):
        self.tratar("GET")

    def do_POST(self):
        self.tratar("POST")

    def do_PUT(self):
        self.tratar("PUT")

    def tratar(self, metodo):
        url = urlsplit(self.path)
        caminho = url.path
        fila = self.server.fila
        try:
            if metodo == "POST" and caminho == "/pedidos":
                campos = self.formulario()
                id_pedido = campos.pop("id", "")
                operacao = campos.get("operacao")
                campos_esperados = {"operacao", "codigo"}
                if operacao == "venda":
                    campos_esperados.update(("quantidade", "receita"))
                if (
                    not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", id_pedido)
                    or operacao not in ("venda", "estoque")
                    or set(campos) != campos_esperados
                    or not campos["codigo"]
                ):
                    raise ErroHTTP(400, "Pedido inválido")
                self.json(202, fila.publicar(id_pedido, campos))
            elif metodo == "GET" and caminho == "/fila":
                cursor = int(dict(parse_qsl(url.query)).get("apos", "0"))
                if not 0 <= cursor <= 2**63 - 1:
                    raise ErroHTTP(400, "Cursor inválido")
                pedido = fila.proximo(cursor)
                if pedido is None:
                    self.responder(204)
                    return
                dados = json.loads(pedido["dados"])
                dados.update(id=pedido["id"], sequencia=pedido["sequencia"],
                             estado="pendente" if pedido["resultado"] is None else "finalizado")
                self.responder(200, urlencode(dados).encode(), "application/x-www-form-urlencoded")
            elif metodo == "GET" and re.fullmatch(r"/pedidos/[a-zA-Z0-9_-]{1,64}", caminho):
                self.json(200, fila.consultar(caminho.split("/")[-1]))
            elif metodo == "PUT" and re.fullmatch(r"/fila/[a-zA-Z0-9_-]{1,64}", caminho):
                resultado = self.formulario()
                if resultado.get("status") not in ("vendido", "rejeitado", "consultado"):
                    raise ErroHTTP(400, "Resultado inválido")
                fila.concluir(caminho.split("/")[-1], resultado)
                self.responder(204)
            else:
                raise ErroHTTP(404, "Rota inexistente")
        except ErroHTTP as erro:
            self.json(erro.status, {"erro": str(erro)})
        except ValueError:
            self.json(400, {"erro": "Parâmetros inválidos"})
        except sqlite3.Error as erro:
            self.log_error("SQLite: %s", erro)
            self.json(503, {"erro": "Fila temporariamente indisponível"})

    def formulario(self):
        if self.headers.get_content_type() != "application/x-www-form-urlencoded":
            raise ErroHTTP(415, "Use application/x-www-form-urlencoded")
        tamanho = int(self.headers.get("Content-Length", "0"))
        if not 0 < tamanho <= 4096:
            raise ErroHTTP(400, "Corpo inválido")
        pares = parse_qsl(self.rfile.read(tamanho).decode("utf-8"), keep_blank_values=True,
                          strict_parsing=True, max_num_fields=12, errors="strict")
        campos = dict(pares)
        if len(pares) != len(campos):
            raise ErroHTTP(400, "Campo duplicado")
        return campos

    def json(self, status, dados):
        self.responder(status, json.dumps(dados, ensure_ascii=False).encode(), "application/json")

    def responder(self, status, corpo=b"", tipo="application/octet-stream"):
        self.send_response(status)
        if status != 204:
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        if corpo:
            self.wfile.write(corpo)

    def log_request(self, code="-", size="-"):
        if self.command != "GET" or self.path.split("?")[0] != "/fila" or code != 204:
            super().log_request(code, size)


def main():
    parser = argparse.ArgumentParser(description="Broker persistente da farmácia")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--porta", type=int, default=8040)
    parser.add_argument("--banco", default="farmacia.sqlite3")
    args = parser.parse_args()
    fila = Fila(args.banco)
    with ThreadingHTTPServer((args.host, args.porta), API) as servidor:
        servidor.fila = fila
        print(f"Broker em http://{args.host}:{servidor.server_port}", flush=True)
        servidor.serve_forever()


if __name__ == "__main__":
    main()
