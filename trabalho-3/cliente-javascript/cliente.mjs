#!/usr/bin/env node
// Cliente HTTP independente; Node.js 18+ (fetch nativo), sem npm install.
import readline from 'node:readline';

const [url = 'http://127.0.0.1:8080', login = 'cliente', senha = '1234'] = process.argv.slice(2);
let token;
let cursor = 0;
let parar = false;
let entrada;

async function requisitar(method, caminho, dados) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  const resposta = await fetch(url.replace(/\/$/, '') + caminho, {
    method, headers, body: dados === undefined ? undefined : JSON.stringify(dados),
    signal: AbortSignal.timeout(5000),
  });
  const resultado = await resposta.json();
  if (!resposta.ok) throw new Error(`HTTP ${resposta.status}: ${resultado.erro}`);
  return resultado;
}

async function escutar() {
  while (!parar) {
    try {
      for (const aviso of await requisitar('GET', `/api/notificacoes?apos=${cursor}`)) {
        console.log('NOTIFICAÇÃO: ' + JSON.stringify(aviso));
        cursor = Number(aviso.id);
      }
    } catch (erro) {
      if (!parar) console.error('Falha na consulta: ' + erro.message);
    }
    if (!parar) await new Promise(resolve => setTimeout(resolve, 500));
  }
}

async function comando(linha) {
  if (parar) return;
  const texto = linha.trim();
  if (!texto) return;
  if (texto === 'sair') { parar = true; entrada.close(); return; }
  try {
    let resultado;
    const [acao, codigo, quantidade, receita, ...extras] = texto.split(/\s+/);
    if (texto === 'perfil') resultado = await requisitar('GET', '/api/perfil');
    else if (acao === 'estoque' && !quantidade) {
      const caminho = codigo ? '/api/estoque?' + new URLSearchParams({ codigo }) : '/api/estoque';
      resultado = await requisitar('GET', caminho);
    } else if (acao === 'venda' && quantidade && !extras.length) {
      resultado = await requisitar('POST', '/api/vendas', { codigo, quantidade, receita });
    } else if (texto === 'atendimentos') resultado = await requisitar('GET', '/api/vendas');
    else if (texto === 'historico') resultado = await requisitar('GET', '/api/notificacoes');
    else {
      const partes = /^publicar\s+(\S+)\s+(.+)$/.exec(texto);
      if (!partes) {
        console.log('Comando inválido. Uso: perfil | estoque [CODIGO] | venda CODIGO QTD [RECEITA] | atendimentos | historico | publicar TIPO mensagem | sair');
        return;
      }
      resultado = await requisitar('POST', '/api/notificacoes', { tipo: partes[1], mensagem: partes[2] });
    }
    console.log(JSON.stringify(resultado));
  } catch (erro) { console.error(erro.message); }
}

try {
  ({ token } = await requisitar('POST', '/api/sessoes', { login, senha }));
  const escuta = escutar();
  console.log('Autenticado. Comandos: perfil | estoque [CODIGO] | venda CODIGO QTD [RECEITA] | atendimentos | historico | publicar TIPO mensagem | sair');
  entrada = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
  let fila = Promise.resolve();
  process.once('SIGINT', () => entrada.close());
  await new Promise(resolve => {
    entrada.on('line', linha => { fila = fila.then(() => comando(linha)); });
    entrada.on('close', resolve);
  });
  await fila;
  parar = true;
  await escuta;
} catch (erro) {
  console.error('Falha: ' + erro.message);
  process.exitCode = 1;
} finally {
  if (token) {
    try { await requisitar('DELETE', '/api/sessoes'); console.log('Sessão encerrada'); }
    catch (erro) { console.error('Falha ao encerrar: ' + erro.message); process.exitCode = 1; }
  }
}
