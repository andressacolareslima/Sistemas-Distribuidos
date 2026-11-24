"""Integração real: servidor Java e clientes Python/JavaScript em processos separados."""
import json
from pathlib import Path
import queue
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import threading
import time
import urllib.error
import urllib.request

BASE = Path(__file__).resolve().parents[1]
processos = []


def iniciar(args):
    p = subprocess.Popen(args, cwd=BASE, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, encoding='utf-8', bufsize=1)
    processos.append(p)
    return p


def api(method, path, data=None, token=None, status=200, content_type='application/json'):
    headers = {'Content-Type': content_type}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    body = data if isinstance(data, bytes) else (json.dumps(data).encode() if data is not None else None)
    req = urllib.request.Request(url + path, body, headers, method=method)
    try:
        response = urllib.request.urlopen(req, timeout=5)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        assert response.code == status, (method, path, response.code, status, response.read())
        result = json.load(response)
        assert response.headers['X-Request-Id']
        if status >= 400:
            assert result['requestId'] == response.headers['X-Request-Id']
        return result


class Console:
    def __init__(self, args):
        self.p = iniciar(args)
        self.fila = queue.Queue()
        self.saida = []
        def ler():
            for line in self.p.stdout:
                self.fila.put(line)
        threading.Thread(target=ler, daemon=True).start()
        self.esperar('Autenticado.')

    def enviar(self, line):
        self.p.stdin.write(line + '\n')
        self.p.stdin.flush()

    def esperar(self, text):
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            try:
                line = self.fila.get(timeout=0.2)
                self.saida.append(line)
                if text in line:
                    return line
            except queue.Empty:
                pass
        raise AssertionError((text, self.saida, self.p.poll()))

    def sair(self):
        self.enviar('sair')
        self.esperar('Sessão encerrada')
        assert self.p.wait(timeout=8) == 0, self.saida


compilacao = TemporaryDirectory()
try:
    classes = Path(compilacao.name)
    subprocess.run(['javac', '-encoding', 'UTF-8', '-d', str(classes),
                    *map(str, sorted((BASE / 'servidor/src/farmacia').glob('*.java')))], check=True)
    servidor = iniciar(['java', '-cp', str(classes), 'farmacia.Servidor', '127.0.0.1', '0'])
    line = servidor.stdout.readline().strip()
    assert 'Farmácia API pronta em ' in line, line
    url = line.split(' em ', 1)[1]
    api('POST', '/api/sessoes', {'login': 'cliente', 'senha': 'errada'}, status=401)
    api('GET', '/api/perfil', status=401)
    token = api('POST', '/api/sessoes', {'login': 'cliente', 'senha': '1234'}, status=201)['token']
    assert api('GET', '/api/perfil', token=token)['perfil'] == 'CLIENTE'
    api('POST', '/api/notificacoes', {'tipo': 'ALERTA', 'mensagem': 'Proibido'}, token, 403)
    admin = api('POST', '/api/sessoes', {'login': 'admin', 'senha': '1234'}, status=201)['token']
    assert len(api('GET', '/api/estoque', token=token)) == 5
    assert api('GET', '/api/estoque?codigo=COM-01', token=token)['estoque'] == '20'
    api('GET', '/api/estoque?codigo=ZZZ-99', token=token, status=404)
    api('GET', '/api/estoque?codigo=COM-01', status=401)
    api('POST', '/api/vendas', {'codigo': 'COM-01', 'quantidade': '1'}, token, 403)
    api('POST', '/api/vendas', {'codigo': 'COM-01', 'quantidade': '0'}, admin, 400)
    api('POST', '/api/vendas', {'codigo': 'COM-01', 'quantidade': '21'}, admin, 409)
    controlado = {'codigo': 'CTL-01', 'quantidade': '1'}
    api('POST', '/api/vendas', controlado, admin, 400)
    assert api('GET', '/api/estoque?codigo=CTL-01', token=token)['estoque'] == '8'
    controlado['receita'] = 'DEMO-CTL-01'
    assert api('POST', '/api/vendas', controlado, admin, 201)['estoque'] == '7'
    api('POST', '/api/vendas', controlado, admin, 409)
    assert api('GET', '/api/estoque?codigo=CTL-01', token=token)['estoque'] == '7'
    api('POST', '/api/notificacoes', {'tipo': 'OUTRO', 'mensagem': 'Inválido'}, admin, 400)
    api('POST', '/api/notificacoes', {'tipo': 'ALERTA', 'mensagem': ' '}, admin, 400)
    api('POST', '/api/notificacoes', b'{', admin, 400)
    api('POST', '/api/notificacoes', b'{}', admin, 415, 'text/plain')
    api('POST', '/api/notificacoes', b' ' * 16385, admin, 413)
    api('GET', '/api/notificacoes?apos=errado', token=token, status=400)
    api('GET', '/api/notificacoes?apos=' + '9' * 100, token=token, status=400)
    api('GET', '/inexistente', token=token, status=404)
    api('PUT', '/api/perfil', token=token, status=405)
    python = [sys.executable, '-u', 'cliente-python/cliente.py', url]
    node = [shutil.which('node') or 'node', 'cliente-javascript/cliente.mjs', url]
    clientes = [Console(python + ['cliente']), Console(node + ['cliente'])]
    # Cada linguagem também publica como funcionário, além de receber como cliente.
    for index, command in enumerate([python, node]):
        funcionario = Console(command + ['admin'])
        funcionario.enviar('perfil')
        funcionario.esperar('FUNCIONARIO')
        funcionario.enviar('estoque COM-01')
        assert json.loads(funcionario.esperar('"estoque"'))['estoque'] == str(20 - index)
        funcionario.enviar('venda COM-01 1')
        assert json.loads(funcionario.esperar('"quantidade"'))['estoque'] == str(19 - index)
        funcionario.enviar('atendimentos')
        assert len(json.loads(funcionario.esperar('"quantidade"'))) == 2 + index
        for tipo in ['NOTIFICACAO', 'ALERTA', 'ATUALIZACAO']:
            mensagem = f'{index} {tipo} Estoque: ação, "aspas" e barra \\ fim'
            funcionario.enviar(f'publicar {tipo} {mensagem}')
            funcionario.esperar('"timestamp"')
            for cliente in clientes:
                line = cliente.esperar('NOTIFICAÇÃO:')
                payload = json.loads(line.split('NOTIFICAÇÃO: ', 1)[1])
                assert payload['mensagem'] == mensagem, payload
                assert payload['tipo'] == tipo and payload['autor'] == 'admin', payload
        funcionario.sair()
    for cliente in clientes:
        cliente.enviar('publicar ALERTA Proibido')
        cliente.esperar('HTTP 403')
        cliente.enviar('inexistente')
        cliente.esperar('Comando inválido')
        cliente.enviar('historico')
        cliente.esperar('Estoque')
        cliente.sair()
    historico = api('GET', '/api/notificacoes', token=token)
    assert len(historico) == 6, historico
    assert [int(n['id']) for n in historico] == list(range(1, 7))
    assert len(api('GET', '/api/notificacoes?apos=4', token=token)) == 2
    assert api('GET', '/api/notificacoes?apos=6', token=token) == []
    api('DELETE', '/api/sessoes', token=token)
    api('GET', '/api/notificacoes', token=token, status=401)
    for command in [python, node]:
        p = iniciar(command + ['cliente', 'errada'])
        out = p.communicate(timeout=10)[0]
        assert p.returncode != 0 and 'HTTP 401' in out, out
    print('OK: API, sessões, estoque, vendas, receitas, atendimentos e avisos '
          'validados com os clientes Python e JavaScript.')
finally:
    for p in processos:
        if p.poll() is None:
            p.terminate()
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()
    compilacao.cleanup()
