#!/usr/bin/env python3
"""Cliente HTTP independente; apenas biblioteca padrão do Python 3.10+."""
import argparse
import json
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request


class Cliente:
    def __init__(self, url):
        self.url = url.rstrip('/')
        self.token = None
        self.cursor = 0

    def requisitar(self, metodo, caminho, dados=None):
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        corpo = None if dados is None else json.dumps(dados).encode('utf-8')
        req = urllib.request.Request(self.url + caminho, corpo, headers, method=metodo)
        try:
            with urllib.request.urlopen(req, timeout=5) as resposta:
                return json.load(resposta)
        except urllib.error.HTTPError as erro:
            raise RuntimeError(f'HTTP {erro.code}: {json.load(erro)["erro"]}') from erro

    def escutar(self, parar):
        while not parar.is_set():
            try:
                for aviso in self.requisitar('GET', f'/api/notificacoes?apos={self.cursor}'):
                    print('NOTIFICAÇÃO: ' + json.dumps(aviso, ensure_ascii=False), flush=True)
                    self.cursor = int(aviso['id'])
            except (RuntimeError, OSError) as erro:
                if not parar.is_set():
                    print('Falha na consulta: ' + str(erro), flush=True)
            parar.wait(0.5)

    def executar(self, login, senha):
        self.token = self.requisitar('POST', '/api/sessoes', {'login': login, 'senha': senha})['token']
        parar = threading.Event()
        thread = threading.Thread(target=self.escutar, args=(parar,), daemon=True)
        thread.start()
        print('Autenticado. Comandos: perfil | estoque [CODIGO] | venda CODIGO QTD [RECEITA] | atendimentos | historico | publicar TIPO mensagem | sair', flush=True)
        try:
            for linha in sys.stdin:
                comando = linha.strip().split(maxsplit=2)
                if not comando:
                    continue
                try:
                    if comando[0] == 'sair':
                        break
                    if comando[0] == 'perfil':
                        resultado = self.requisitar('GET', '/api/perfil')
                    elif comando[0] == 'estoque' and len(comando) <= 2:
                        query = urllib.parse.urlencode({'codigo': comando[1]}) if len(comando) == 2 else ''
                        caminho = '/api/estoque?' + query if query else '/api/estoque'
                        resultado = self.requisitar('GET', caminho)
                    elif comando[0] == 'venda' and len(comando) == 3:
                        valores = comando[2].split()
                        if len(valores) not in (1, 2):
                            print('Uso: venda CODIGO QTD [RECEITA]', flush=True)
                            continue
                        dados = {'codigo': comando[1], 'quantidade': valores[0]}
                        if len(valores) == 2:
                            dados['receita'] = valores[1]
                        resultado = self.requisitar('POST', '/api/vendas', dados)
                    elif comando == ['atendimentos']:
                        resultado = self.requisitar('GET', '/api/vendas')
                    elif comando[0] == 'historico':
                        resultado = self.requisitar('GET', '/api/notificacoes')
                    elif comando[0] == 'publicar' and len(comando) == 3:
                        resultado = self.requisitar('POST', '/api/notificacoes',
                                                    {'tipo': comando[1], 'mensagem': comando[2]})
                    else:
                        print('Comando inválido. Uso: perfil | estoque [CODIGO] | venda CODIGO QTD [RECEITA] | atendimentos | historico | publicar TIPO mensagem | sair', flush=True)
                        continue
                    print(json.dumps(resultado, ensure_ascii=False), flush=True)
                except (RuntimeError, OSError) as erro:
                    print(str(erro), flush=True)
        finally:
            parar.set()
            thread.join(timeout=6)
            self.requisitar('DELETE', '/api/sessoes')
            print('Sessão encerrada', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('url', nargs='?', default='http://127.0.0.1:8080')
    parser.add_argument('login', nargs='?', default='cliente')
    parser.add_argument('senha', nargs='?', default='1234')
    args = parser.parse_args()
    try:
        Cliente(args.url).executar(args.login, args.senha)
    except (RuntimeError, OSError) as erro:
        parser.exit(1, f'Falha: {erro}\n')
    except KeyboardInterrupt:
        pass
