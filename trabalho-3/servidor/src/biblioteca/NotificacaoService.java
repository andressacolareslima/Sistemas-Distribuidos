package biblioteca;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

/** Objeto remoto de publicação e consulta; estado compartilhado por todos os clientes. */
public final class NotificacaoService {
    private record Notificacao(long id, String tipo, String mensagem, long timestamp, Usuario autor) {
        String toJson() {
            return Json.encode(Map.of("id", Long.toString(id), "tipo", tipo, "mensagem", mensagem,
                "timestamp", Long.toString(timestamp), "autor", autor.getNome(), "perfil", autor.getPerfil()));
        }
    }
    private final List<Notificacao> historico = new ArrayList<>();

    public synchronized String publicar(Usuario usuario, Map<String, String> dados) {
        if (!(usuario instanceof Funcionario))
            throw new ApiException(403, "Publicação exige funcionário");
        String tipo = Json.required(dados, "tipo");
        String mensagem = Json.required(dados, "mensagem");
        if (!Set.of("NOTIFICACAO", "ALERTA", "ATUALIZACAO").contains(tipo))
            throw new ApiException(400, "Tipo inválido");
        if (mensagem.length() > 4000) throw new ApiException(400, "Mensagem excede 4000 caracteres");
        Notificacao n = new Notificacao(historico.size() + 1L, tipo, mensagem,
                                       System.currentTimeMillis(), usuario);
        historico.add(n);
        return n.toJson();
    }

    public synchronized String listar(long apos) {
        if (apos < 0) throw new ApiException(400, "Cursor inválido");
        return historico.stream().filter(n -> n.id() > apos).map(Notificacao::toJson)
            .collect(Collectors.joining(",", "[", "]"));
    }
}
