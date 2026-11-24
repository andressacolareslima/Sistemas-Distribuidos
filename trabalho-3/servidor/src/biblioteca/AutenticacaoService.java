package biblioteca;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/** Objeto remoto de autenticação, exposto por /api/sessoes. */
public final class AutenticacaoService {
    private final Map<String, Usuario> sessoes = new ConcurrentHashMap<>();

    public String autenticar(Map<String, String> dados) {
        String login = Json.required(dados, "login");
        String senha = Json.required(dados, "senha");
        if (!"1234".equals(senha) || !(login.equals("aluno") || login.equals("admin")))
            throw new ApiException(401, "Credenciais inválidas");
        Usuario usuario = login.equals("admin") ? new Funcionario(login) : new Aluno(login);
        String token = UUID.randomUUID().toString();
        sessoes.put(token, usuario);
        return token;
    }

    public Usuario exigirUsuario(String authorization) {
        if (authorization == null || !authorization.startsWith("Bearer "))
            throw new ApiException(401, "Autenticação obrigatória");
        Usuario usuario = sessoes.get(authorization.substring(7));
        if (usuario == null) throw new ApiException(401, "Sessão inválida ou encerrada");
        return usuario;
    }

    public void sair(String authorization) {
        exigirUsuario(authorization);
        sessoes.remove(authorization.substring(7));
    }
}
