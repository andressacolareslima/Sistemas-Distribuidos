# Trabalho 4 — Sistema de Gestão de Farmácia

- **Equipe 31:** Andressa Colares (471151)
- **Disciplina:** Sistemas Distribuídos — Ciência da Computação, 2026.2

O balcão envia pedidos de venda a uma fila persistente em SQLite. O consumidor em JavaScript valida a receita de demonstração, atualiza o estoque e registra o atendimento. Os pedidos ficam na fila enquanto o consumidor estiver desligado.

[Relatório técnico (PDF)](relatorio-tecnico.pdf)

## Diagrama de classes

O diagrama mostra o catálogo e as vendas no consumidor JavaScript, além das classes da API e da fila persistente no broker Python.

```mermaid
classDiagram
    class Vendas {
        <<interface>>
        +verificarReceita(medicamento, receita)
        +atualizarEstoque(medicamento, quantidade)
        +registrarAtendimento(atendimento)
    }

    class Farmacia["Farmácia"] {
        -Map medicamentos
        -Map atendimentos
        -Set receitasUtilizadas
        +demonstracao()$
        +processar(pedido)
    }

    class Medicamento {
        <<abstract>>
        +String codigo
        +String nome
        -Number estoque
        +exigeReceita() boolean
        +baixarEstoque(quantidade)
    }

    class MedicamentoControlado {
        +exigeReceita() boolean
    }
    class MedicamentoComum
    class Cosmetico["Cosmético"]
    class Suplemento
    class EquipamentoHospitalar

    Vendas <|-- Farmacia
    Farmacia "1" --> "0..*" Medicamento : mantém no catálogo
    Medicamento <|-- MedicamentoControlado
    Medicamento <|-- MedicamentoComum
    Medicamento <|-- Cosmetico
    Medicamento <|-- Suplemento
    Medicamento <|-- EquipamentoHospitalar

    class API {
        +do_GET()
        +do_POST()
        +do_PUT()
    }

    class Fila {
        +publicar(id_pedido, campos)
        +consultar(id_pedido)
        +proximo(cursor)
        +concluir(id_pedido, resultado)
    }

    BaseHTTPRequestHandler <|-- API
    API ..> Fila : encaminha operações
```

`Vendas` é um contrato representado por uma classe base em JavaScript. O balcão e o consumidor comunicam-se com o broker por HTTP.

## Como executar

Use Python 3.9+ e Node.js 18+. Na pasta `trabalho-4`, inicie o broker:

```sh
python3 broker.py
```

Em outro terminal, envie uma venda com o consumidor desligado. O pedido aparecerá como `pendente`:

```sh
python3 balcao.py venda COM-01 2 --id venda-demo
```

Inicie o consumidor em um terceiro terminal:

```sh
node src/farmacia/consumidor.mjs
```

Consulte o resultado no terminal do balcão:

```sh
python3 balcao.py status venda-demo
```
