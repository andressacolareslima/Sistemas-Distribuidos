package farmacia;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

public final class FarmaciaService {
    private record Produto(String codigo, String nome, String categoria, int estoque) {
        boolean exigeReceita() {
            return categoria.equals("MedicamentoControlado");
        }

        Map<String, String> dados() {
            return Map.of("codigo", codigo, "nome", nome, "categoria", categoria,
                          "estoque", Integer.toString(estoque));
        }

        Produto baixarEstoque(int quantidade) {
            return new Produto(codigo, nome, categoria, estoque - quantidade);
        }
    }

    private final Map<String, Produto> catalogo = new LinkedHashMap<>();
    private final Set<String> receitasUtilizadas = new HashSet<>();
    private final List<String> atendimentos = new ArrayList<>();

    public FarmaciaService() {
        for (Produto produto : List.of(
                new Produto("CTL-01", "Medicamento controlado de demonstração", "MedicamentoControlado", 8),
                new Produto("COM-01", "Analgésico de demonstração", "MedicamentoComum", 20),
                new Produto("COS-01", "Hidratante", "Cosmético", 12),
                new Produto("SUP-01", "Suplemento vitamínico", "Suplemento", 10),
                new Produto("EQH-01", "Termômetro digital", "EquipamentoHospitalar", 6))) {
            catalogo.put(produto.codigo(), produto);
        }
    }

    private Produto buscar(String codigo) {
        Produto produto = catalogo.get(codigo);
        if (produto == null) throw new ApiException(404, "Produto desconhecido");
        return produto;
    }

    public synchronized String consultar(String query) {
        if (query == null) {
            return "[" + String.join(",", catalogo.values().stream()
                    .map(produto -> Json.encode(produto.dados())).toList()) + "]";
        }
        if (!query.matches("codigo=[A-Z]{3}-[0-9]{2}"))
            throw new ApiException(400, "Use ?codigo=XXX-00");
        return Json.encode(buscar(query.substring("codigo=".length())).dados());
    }

    public synchronized String vender(Usuario funcionario, Map<String, String> dados) {
        Produto produto = buscar(Json.required(dados, "codigo"));
        int quantidade = Integer.parseInt(Json.required(dados, "quantidade"));
        if (quantidade <= 0) throw new ApiException(400, "Quantidade deve ser positiva");
        if (quantidade > produto.estoque()) throw new ApiException(409, "Estoque insuficiente");

        String receita = dados.get("receita");
        if (produto.exigeReceita()) {
            if (!("DEMO-" + produto.codigo()).equals(receita))
                throw new ApiException(400, "Receita de demonstração inválida");
            if (receitasUtilizadas.contains(receita))
                throw new ApiException(409, "Receita de demonstração já utilizada");
        }

        Produto atualizado = produto.baixarEstoque(quantidade);
        var atendimento = new LinkedHashMap<>(atualizado.dados());
        atendimento.put("id", Long.toString(atendimentos.size() + 1L));
        atendimento.put("quantidade", Integer.toString(quantidade));
        atendimento.put("funcionario", funcionario.getNome());
        String resposta = Json.encode(atendimento);
        catalogo.put(produto.codigo(), atualizado);
        if (produto.exigeReceita()) receitasUtilizadas.add(receita);
        atendimentos.add(resposta);
        return resposta;
    }

    public synchronized String atendimentos() {
        return "[" + String.join(",", atendimentos) + "]";
    }
}
