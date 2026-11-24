export class Medicamento {
    #estoque;

    constructor(codigo, nome, estoque) {
        if (new.target === Medicamento) {
            throw new TypeError("Instancie uma categoria de medicamento");
        }
        if (!Number.isSafeInteger(estoque) || estoque < 0) {
            throw new RangeError("Estoque inicial inválido");
        }
        this.codigo = codigo;
        this.nome = nome;
        this.#estoque = estoque;
    }

    get estoque() {
        return this.#estoque;
    }

    get categoria() {
        return this.constructor.name;
    }

    exigeReceita() {
        return false;
    }

    baixarEstoque(quantidade) {
        if (!Number.isSafeInteger(quantidade) || quantidade <= 0 || quantidade > this.#estoque) {
            throw new RangeError("Quantidade inválida ou estoque insuficiente");
        }
        this.#estoque -= quantidade;
    }
}

export class MedicamentoControlado extends Medicamento {
    exigeReceita() {
        return true;
    }
}

export class MedicamentoComum extends Medicamento {}
export class Cosmético extends Medicamento {}
export class Suplemento extends Medicamento {}
export class EquipamentoHospitalar extends Medicamento {}
