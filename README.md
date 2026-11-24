# Sistemas Distribuídos — 2026.2

- **Aluna:** Andressa Colares
- **Matrícula:** 471151
- **Curso:** Ciência da Computação
- **Disciplina:** Sistemas Distribuídos

Os Trabalhos 1 e 2 têm um tema diferente dos Trabalhos 3 e 4. Quando implementei os dois primeiros, achei que a escolha do tema era livre. Só soube das opções de tema da disciplina depois de concluir as duas implementações. Por isso, os Trabalhos 1 e 2 usam o tema de biblioteca. Reimplementei o Trabalho 3 com o mesmo tema do Trabalho 4, o Sistema de Gestão de Farmácia.

As versões iniciais dos Trabalhos 1, 2 e 3 foram publicadas no [repositório original da disciplina](https://github.com/andressacolareslima/QXD0043-Sistemas-Distribuidos). O Trabalho 4 foi desenvolvido neste repositório.

Execute os comandos de cada seção a partir da raiz do repositório, em terminais separados quando indicado.

## [Trabalho 1 — Biblioteca com streams, sockets e multicast](trabalho-1/)

Implementação em Java com serialização de livros para streams, arquivos e conexões TCP. Um protocolo de requisição e resposta permite cadastrar e buscar livros. Os clientes autenticados podem receber avisos por multicast.

[Vídeo de demonstração](trabalho-1/demonstracao.mp4) · [Relatório técnico (PDF)](trabalho-1/relatorio-tecnico.pdf)

Compile e execute o teste integrado com um JDK:

```sh
cd trabalho-1
mkdir -p target/classes
javac -encoding UTF-8 -d target/classes src/biblioteca/*.java
java -cp target/classes biblioteca.TesteIntegrado
```

Para experimentar o RPC, execute `java -cp target/classes biblioteca.Main rpc-servidor` e, em outro terminal na mesma pasta, `java -cp target/classes biblioteca.Main rpc-cliente localhost`.

## [Trabalho 2 — Biblioteca com Java RMI](trabalho-2/)

O servidor autentica alunos e funcionários, mantém o histórico de notificações e distribui avisos por callbacks remotos. Funcionários podem publicar notificações, alertas e atualizações. As operações usam mensagens JSON de requisição e resposta sobre RMI.

[Vídeo de demonstração](trabalho-2/demonstracao.mp4) · [Relatório técnico (PDF)](trabalho-2/relatorio-tecnico.pdf)

Compile e rode o teste entre processos com um JDK e Python 3:

```sh
cd trabalho-2
mkdir -p target/classes
javac -encoding UTF-8 -d target/classes src/biblioteca/*.java
python3 validar.py
```

Para uso manual, inicie `java -cp target/classes biblioteca.Servidor` e rode `java -cp target/classes biblioteca.Cliente 127.0.0.1 aluno 1234` em outro terminal na mesma pasta. Use `admin` no lugar de `aluno` para publicar avisos.

## [Trabalho 3 — Sistema de Gestão de Farmácia com HTTP/JSON](trabalho-3/)

Uma API HTTP/JSON em Java atende clientes independentes em Python e JavaScript. Clientes autenticados consultam estoque e recebem avisos por consultas periódicas. Funcionários também registram vendas, consultam atendimentos e publicam avisos. Vendas de medicamentos controlados exigem uma receita de demonstração de uso único. Estoque, receitas utilizadas, atendimentos e avisos ficam em memória durante a execução do servidor.

O vídeo e o relatório do Trabalho 3 documentam a versão original da API de notificações da biblioteca, anterior à reimplementação em farmácia. [Vídeo da versão original](trabalho-3/demonstracao-versao-original.mp4) · [Relatório da versão original (PDF)](trabalho-3/relatorio-versao-original.pdf)

Com JDK 17+, Python 3.10+ e Node.js 18+, inicie o servidor:

```sh
cd trabalho-3
mkdir -p servidor/target/classes
javac -encoding UTF-8 -d servidor/target/classes servidor/src/farmacia/*.java
java -cp servidor/target/classes farmacia.Servidor
```

Em dois terminais na pasta `trabalho-3`, abra um cliente e uma sessão de funcionário:

```sh
python3 cliente-python/cliente.py http://127.0.0.1:8080 cliente 1234
node cliente-javascript/cliente.mjs http://127.0.0.1:8080 admin 1234
```

Use `estoque` para listar produtos ou `estoque COM-01` para consultar um item. Na sessão de funcionário, experimente `venda COM-01 2`, `venda CTL-01 1 DEMO-CTL-01`, `atendimentos` e `publicar ATUALIZACAO Estoque atualizado`. Use `historico` para listar avisos e `sair` para encerrar a sessão.

O comando `python3 testes/validar.py`, executado em `trabalho-3`, compila e inicia um servidor separado e testa os dois clientes.

## [Trabalho 4 — Sistema de Gestão de Farmácia com fila persistente](trabalho-4/)

O balcão em Python envia pedidos para um broker com fila persistente em SQLite. Um consumidor em JavaScript processa consultas e vendas, valida receitas, atualiza o estoque e registra atendimentos. Os pedidos pendentes permanecem na fila enquanto o consumidor estiver desligado.

Use Python 3.9+ e Node.js 18+. A partir da pasta `trabalho-4`, inicie cada processo contínuo em um terminal separado:

| Etapa | Comando |
| --- | --- |
| Iniciar o broker | `python3 broker.py` |
| Enviar uma venda | `python3 balcao.py venda COM-01 2 --id venda-demo` |
| Iniciar o consumidor | `node src/farmacia/consumidor.mjs` |
| Consultar o resultado | `python3 balcao.py status venda-demo` |

[Instruções do Trabalho 4](trabalho-4/README.md) · [Relatório técnico (PDF)](trabalho-4/relatorio-tecnico.pdf)
