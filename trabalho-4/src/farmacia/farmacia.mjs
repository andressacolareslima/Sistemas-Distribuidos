import {
    Cosmético, EquipamentoHospitalar, MedicamentoComum, MedicamentoControlado, Suplemento,
} from "./medicamentos.mjs";

/**
 * @interface
 */
export class Vendas {
    verificarReceita(medicamento, receita) {
        throw new TypeError("Implemente verificarReceita");
    }

    atualizarEstoque(medicamento, quantidade) {
        throw new TypeError("Implemente atualizarEstoque");
    }

    registrarAtendimento(atendimento) {
        throw new TypeError("Implemente registrarAtendimento");
    }
}

export class Farmacia extends Vendas {
    #medicamentos = new Map();
    #atendimentos = new Map();
    #receitasUtilizadas = new Set();

    constructor(catalogo) {
        super();
        for (const medicamento of catalogo) {
            if (this.#medicamentos.has(medicamento.codigo)) {
                throw new Error("Código duplicado no catálogo");
            }
            this.#medicamentos.set(medicamento.codigo, medicamento);
        }
    }

    static demonstracao() {
        return new Farmacia([
            new MedicamentoControlado("CTL-01", "Medicamento controlado de demonstração", 8),
            new MedicamentoComum("COM-01", "Analgésico de demonstração", 20),
            new Cosmético("COS-01", "Hidratante", 12),
            new Suplemento("SUP-01", "Suplemento vitamínico", 10),
            new EquipamentoHospitalar("EQH-01", "Termômetro digital", 6),
        ]);
    }

    verificarReceita(medicamento, receita) {
        return !medicamento.exigeReceita()
            || (receita === `DEMO-${medicamento.codigo}` && !this.#receitasUtilizadas.has(receita));
    }

    atualizarEstoque(medicamento, quantidade) {
        medicamento.baixarEstoque(quantidade);
    }

    registrarAtendimento(atendimento) {
        this.#atendimentos.set(atendimento.pedido, atendimento);
    }

    processar(pedido) {
        try {
            const medicamento = this.#medicamentos.get(pedido.codigo);
            if (!medicamento) {
                throw new RangeError("Produto desconhecido");
            }
            switch (pedido.operacao) {
                case "estoque":
                    return this.#resultado("consultado", medicamento);
                case "venda":
                    return this.#vender(pedido, medicamento);
                default:
                    throw new RangeError("Operação desconhecida");
            }
        } catch (erro) {
            if (!(erro instanceof RangeError)) {
                throw erro;
            }
            return { status: "rejeitado", motivo: erro.message };
        }
    }

    #vender(pedido, medicamento) {
        if (!this.verificarReceita(medicamento, pedido.receita)) {
            throw new RangeError("Receita de demonstração inválida ou já utilizada");
        }
        if (!/^[+-]?\d+$/.test(pedido.quantidade)) {
            throw new RangeError("Quantidade inválida");
        }
        const quantidade = Number(pedido.quantidade);
        this.atualizarEstoque(medicamento, quantidade);
        if (medicamento.exigeReceita()) {
            this.#receitasUtilizadas.add(pedido.receita);
        }
        this.registrarAtendimento({ pedido: pedido.id, codigo: medicamento.codigo, quantidade });
        return this.#resultado("vendido", medicamento);
    }

    #resultado(status, medicamento) {
        return {
            status,
            codigo: medicamento.codigo,
            nome: medicamento.nome,
            categoria: medicamento.categoria,
            estoque: String(medicamento.estoque),
        };
    }
}
