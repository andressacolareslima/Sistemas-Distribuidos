"""Integração real: servidor Java e clientes Python/JavaScript em processos separados."""
import json
from pathlib import Path
import queue
import shutil
import subprocess
import sys
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


try:
    classes = BASE / 'servidor/target/classes'
    classes.mkdir(parents=True, exist_ok=True)
    subprocess.run(['javac', '-encoding', 'UTF-8', '-d', str(classes),
                    *map(str, sorted((BASE / 'servidor/src/biblioteca').glob('*.java')))], check=True)
    servidor = iniciar(['java', '-cp', str(classes), 'biblioteca.Servidor', '127.0.0.1', '0'])
    line = servidor.stdout.readline().strip()
    assert 'Biblioteca API pronta em ' in line, line
    url = line.split(' em ', 1)[1]
    api('POST', '/api/sessoes', {'login': 'aluno', 'senha': 'errada'}, status=401)
    api('GET', '/api/perfil', status=401)
    token = api('POST', '/api/sessoes', {'login': 'aluno', 'senha': '1234'}, status=201)['token']
    assert api('GET', '/api/perfil', token=token)['perfil'] == 'ALUNO'
    api('POST', '/api/notificacoes', {'tipo': 'ALERTA', 'mensagem': 'Proibido'}, token, 403)
    admin = api('POST', '/api/sessoes', {'login': 'admin', 'senha': '1234'}, status=201)['token']
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
    alunos = [Console(python + ['aluno']), Console(node + ['aluno'])]
    # Cada linguagem também publica como funcionário, além de receber como aluno.
    for index, command in enumerate([python, node]):
        funcionario = Console(command + ['admin'])
        funcionario.enviar('perfil')
        funcionario.esperar('FUNCIONARIO')
        for tipo in ['NOTIFICACAO', 'ALERTA', 'ATUALIZACAO']:
            mensagem = f'{index} {tipo} Catálogo: ação, "aspas" e barra \\ fim'
            funcionario.enviar(f'publicar {tipo} {mensagem}')
            funcionario.esperar('"timestamp"')
            for aluno in alunos:
                line = aluno.esperar('NOTIFICAÇÃO:')
                payload = json.loads(line.split('NOTIFICAÇÃO: ', 1)[1])
                assert payload['mensagem'] == mensagem, payload
                assert payload['tipo'] == tipo and payload['autor'] == 'admin', payload
        funcionario.sair()
    for aluno in alunos:
        aluno.enviar('publicar ALERTA Proibido')
        aluno.esperar('HTTP 403')
        aluno.enviar('inexistente')
        aluno.esperar('Comando inválido')
        aluno.enviar('historico')
        aluno.esperar('Catálogo')
        aluno.sair()
    historico = api('GET', '/api/notificacoes', token=token)
    assert len(historico) == 6, historico
    assert [int(n['id']) for n in historico] == list(range(1, 7))
    assert len(api('GET', '/api/notificacoes?apos=4', token=token)) == 2
    assert api('GET', '/api/notificacoes?apos=6', token=token) == []
    api('DELETE', '/api/sessoes', token=token)
    api('GET', '/api/notificacoes', token=token, status=401)
    for command in [python, node]:
        p = iniciar(command + ['aluno', 'errada'])
        out = p.communicate(timeout=10)[0]
        assert p.returncode != 0 and 'HTTP 401' in out, out
    print('OK: API, autenticação, autorização, validação, histórico, cursor, logout e dois clientes reais; '
          'ambas as linguagens publicam e recebem os três tipos de notificação.')
finally:
    for p in processos:
        if p.poll() is None:
            p.terminate()
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()
