import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import urlopen
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser(description="Balcão do Sistema de Gestão de Farmácia")
    parser.add_argument("--broker", default="http://127.0.0.1:8040")
    comandos = parser.add_subparsers(dest="comando", required=True)

    venda = comandos.add_parser("venda")
    venda.add_argument("codigo")
    venda.add_argument("quantidade", type=int)
    venda.add_argument("--receita", default="")
    estoque = comandos.add_parser("estoque")
    estoque.add_argument("codigo")
    for comando in (venda, estoque):
        comando.add_argument("--id", default=None, help="ID para repetir o envio com segurança")
    status = comandos.add_parser("status")
    status.add_argument("id")
    args = parser.parse_args()

    base = args.broker.rstrip("/") + "/pedidos"
    dados = None
    if args.comando == "status":
        url = base + "/" + quote(args.id, safe="")
    else:
        url = base
        args.id = args.id or uuid4().hex
        campos = {"id": args.id, "operacao": args.comando, "codigo": args.codigo}
        if args.comando == "venda":
            campos.update(quantidade=args.quantidade, receita=args.receita)
        dados = urlencode(campos).encode()

    try:
        with urlopen(url, data=dados, timeout=5) as resposta:
            print(json.dumps(json.load(resposta), ensure_ascii=False, indent=2))
    except HTTPError as erro:
        parser.exit(1, f"Pedido {args.id}: HTTP {erro.code}: {erro.read().decode()}\n")
    except (URLError, TimeoutError) as erro:
        parser.exit(1, f"Pedido {args.id}: falha na comunicação com o broker: {erro}\n")


if __name__ == "__main__":
    main()
