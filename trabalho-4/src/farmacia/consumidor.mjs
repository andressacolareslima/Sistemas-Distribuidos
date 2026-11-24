import { setTimeout as esperar } from "node:timers/promises";
import { Farmacia } from "./farmacia.mjs";

const broker = new URL(process.argv[2] ?? "http://127.0.0.1:8040").href.replace(/\/+$/, "");

class ErroComunicacao extends Error {}

async function requisitar(caminho, opcoes = {}) {
    try {
        const resposta = await fetch(broker + caminho, {
            ...opcoes,
            signal: AbortSignal.timeout(5000),
        });
        return { status: resposta.status, corpo: await resposta.text() };
    } catch (erro) {
        throw new ErroComunicacao(erro.message, { cause: erro });
    }
}

function verificarStatus(resposta, esperado) {
    if (resposta.status !== esperado) {
        throw new ErroComunicacao(`HTTP ${resposta.status} ${resposta.corpo}`);
    }
}

async function processarFila() {
    const farmacia = Farmacia.demonstracao();
    let cursor = "0";
    while (true) {
        const resposta = await requisitar(`/fila?apos=${cursor}`);
        if (resposta.status === 204) {
            await esperar(300);
            continue;
        }
        verificarStatus(resposta, 200);
        const pedido = Object.fromEntries(new URLSearchParams(resposta.corpo));
        const resultado = farmacia.processar(pedido);
        if (pedido.estado === "pendente") {
            const confirmacao = await requisitar(`/fila/${encodeURIComponent(pedido.id)}`, {
                method: "PUT",
                body: new URLSearchParams(resultado),
            });
            verificarStatus(confirmacao, 204);
            console.log(`Pedido ${pedido.id}:`, resultado);
        }
        cursor = pedido.sequencia;
    }
}

console.log(`Consumidor iniciado. Fila: ${broker}`);
while (true) {
    try {
        await processarFila();
    } catch (erro) {
        if (!(erro instanceof ErroComunicacao)) {
            throw erro;
        }
        console.error(`Reconectando e reconstruindo o estoque: ${erro.message}`);
        await esperar(1000);
    }
}
