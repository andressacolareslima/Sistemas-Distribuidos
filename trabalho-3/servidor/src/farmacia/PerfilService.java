package farmacia;

import java.util.Map;

/** Objeto remoto de perfis, exposto por /api/perfil. */
public final class PerfilService {
    public String consultar(Usuario usuario) {
        return Json.encode(Map.of("nome", usuario.getNome(), "perfil", usuario.getPerfil()));
    }
}
