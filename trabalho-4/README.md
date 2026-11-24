# Trabalho 4 — Sistema de Gestão de Farmácia

- **Equipe 31:** Andressa Colares — 471151
- **Disciplina:** Sistemas Distribuídos — Ciência da Computação — 2026.2
- **Abordagem:** Opção C — Filas de mensagens

## Arquitetura e justificativa

O balcão envia pedidos de venda ao broker HTTP, que grava cada pedido em uma fila FIFO no SQLite antes de confirmar o recebimento. O consumidor JavaScript busca os pedidos, verifica a receita de demonstração, baixa o estoque e registra o atendimento. O balcão consulta o resultado pelo identificador do pedido.

O balcão e o consumidor conhecem somente o endereço do broker. O balcão pode registrar a solicitação enquanto o consumidor estiver desligado. O broker mantém o pedido pendente mesmo após reiniciar. Essa separação é adequada ao atendimento porque o balcão pode enfileirar solicitações enquanto o serviço responsável pela validação e pelo estoque está indisponível. A venda só é confirmada após o processamento.

A classe base `Medicamento` tem cinco subclasses: `MedicamentoControlado`, `MedicamentoComum`, `Cosmético`, `Suplemento` e `EquipamentoHospitalar`. A classe `Farmacia` agrega o catálogo e implementa o contrato `Vendas` com `verificarReceita`, `atualizarEstoque` e `registrarAtendimento`. O cenário acadêmico usa um catálogo fixo e a receita fictícia `DEMO-CTL-01`, válida para uma venda do item controlado.

## Demonstração prática

Use Python 3.9+ e Node.js 18+. Rode os comandos a partir de `trabalho-4`. Para repetir o cenário do zero, use outro arquivo com `--banco` ao iniciar o broker. IDs iguais no mesmo banco recuperam o pedido existente.

1. Em um terminal, inicie somente o broker.

   ```sh
   python3 broker.py
   ```

2. Em outro terminal, envie as vendas enquanto o consumidor ainda estiver desligado. O resultado da consulta será `pendente`.

   ```sh
   python3 balcao.py venda COM-01 2 --id venda-comum
   python3 balcao.py venda CTL-01 1 --id sem-receita
   python3 balcao.py venda CTL-01 1 --receita DEMO-CTL-01 --id com-receita
   python3 balcao.py status venda-comum
   ```

   Para demonstrar persistência, encerre o broker com Ctrl+C e execute `python3 broker.py` de novo no mesmo diretório. As solicitações ainda estarão pendentes.

3. Em um terceiro terminal, inicie o consumidor.

   ```sh
   node src/farmacia/consumidor.mjs
   ```

4. Consulte os resultados no terminal do balcão. Em uma fila nova, a venda comum termina com estoque 18, a venda sem receita é rejeitada e a venda com receita termina com estoque 7.

   ```sh
   python3 balcao.py status venda-comum
   python3 balcao.py status sem-receita
   python3 balcao.py status com-receita
   python3 balcao.py estoque COM-01 --id estoque-comum
   python3 balcao.py status estoque-comum
   ```

   Se a consulta de estoque ainda estiver pendente, consulte o mesmo ID novamente após o consumidor processá-la. Para provar a recuperação do consumidor, encerre-o, publique outra venda e inicie-o novamente. Use o mesmo ID e os mesmos dados para repetir um envio cujo retorno se perdeu. Se houver máquinas separadas, inicie o broker com `--host 0.0.0.0` em rede de teste e informe sua URL ao balcão com `--broker` e como primeiro argumento do consumidor JavaScript.

## Robustez e custo da indireção

A fila conserva entradas concluídas e pendentes em ordem de chegada. A confirmação do primeiro pedido pendente é atômica no broker. Se o consumidor cair antes de confirmar, o pedido aguarda nova execução. Se cair depois da confirmação, o consumidor reconstrói estoque, receitas usadas e atendimentos reaplicando o histórico concluído ao catálogo inicial. Assim, uma alteração feita apenas em memória é descartada quando a conexão falha, e repetir o envio com o mesmo ID conserva um único registro na fila. O modelo pressupõe catálogo inicial e regras determinísticas durante a reprodução do histórico.

Cada pedido passa pelo broker, com custo de serialização, tráfego HTTP e gravação em disco. A consulta a cada 300 ms limita o tráfego ocioso, ao custo de acrescentar espera quando a fila está vazia. O processamento FIFO serializa as baixas de estoque, e o tempo de recuperação cresce com o histórico. Esses custos foram analisados pela arquitetura, sem benchmark. Em volumes maiores, espera longa no broker reduziria consultas vazias, lotes amortizariam os custos de rede e checkpoints permitiriam restaurar o estoque sem reler todo o histórico. O broker e o SQLite são pontos únicos de falha nesta implementação. O serviço usa HTTP local e se destina à demonstração.
