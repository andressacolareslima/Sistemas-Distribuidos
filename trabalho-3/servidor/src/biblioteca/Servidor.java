package biblioteca;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Executors;

/** HTTP/JSON usando o servidor HTTP do JDK; sem sockets explícitos e sem RMI. */
public final class Servidor {
    private final AutenticacaoService autenticacao = new AutenticacaoService();
    private final PerfilService perfis = new PerfilService();
    private final NotificacaoService notificacoes = new NotificacaoService();

    private Map<String, String> corpo(HttpExchange exchange) throws IOException {
        String contentType = exchange.getRequestHeaders().getFirst("Content-Type");
        if (contentType == null || !contentType.split(";", 2)[0].trim().equalsIgnoreCase("application/json"))
            throw new ApiException(415, "Use Content-Type application/json");
        byte[] bytes = exchange.getRequestBody().readNBytes(16385);
        if (bytes.length > 16384) throw new ApiException(413, "Corpo excede 16 KiB");
        return Json.decode(new String(bytes, StandardCharsets.UTF_8));
    }

    private void metodo(HttpExchange exchange, String permitidos) {
        exchange.getResponseHeaders().set("Allow", permitidos);
        throw new ApiException(405, "Método HTTP não permitido");
    }

    private void atender(HttpExchange exchange) throws IOException {
        String id = UUID.randomUUID().toString();
        exchange.getResponseHeaders().set("X-Request-Id", id);
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        exchange.getResponseHeaders().set("Cache-Control", "no-store");
        int status = 200;
        String resposta;
        try {
            String path = exchange.getRequestURI().getPath();
            String method = exchange.getRequestMethod();
            String authorization = exchange.getRequestHeaders().getFirst("Authorization");
            switch (path) {
                case "/api/sessoes" -> {
                    if (method.equals("POST")) {
                        resposta = Json.encode(Map.of("token", autenticacao.autenticar(corpo(exchange))));
                        status = 201;
                    } else if (method.equals("DELETE")) {
                        autenticacao.sair(authorization);
                        resposta = Json.encode(Map.of("mensagem", "Sessão encerrada"));
                    } else { metodo(exchange, "POST, DELETE"); return; }
                }
                case "/api/perfil" -> {
                    if (!method.equals("GET")) metodo(exchange, "GET");
                    resposta = perfis.consultar(autenticacao.exigirUsuario(authorization));
                }
                case "/api/notificacoes" -> {
                    Usuario usuario = autenticacao.exigirUsuario(authorization);
                    if (method.equals("POST")) {
                        resposta = notificacoes.publicar(usuario, corpo(exchange));
                        status = 201;
                    } else if (method.equals("GET")) {
                        String query = exchange.getRequestURI().getRawQuery();
                        if (query != null && !query.matches("apos=[0-9]+"))
                            throw new ApiException(400, "Use ?apos=ID (inteiro não negativo)");
                        long apos = query == null ? 0 : Long.parseLong(query.substring(5));
                        resposta = notificacoes.listar(apos);
                    } else { metodo(exchange, "GET, POST"); return; }
                }
                default -> throw new ApiException(404, "Recurso desconhecido");
            }
        } catch (ApiException e) {
            status = e.status;
            resposta = Json.encode(Map.of("erro", e.getMessage(), "requestId", id));
        } catch (IllegalArgumentException | IndexOutOfBoundsException e) {
            status = 400;
            resposta = Json.encode(Map.of("erro", "Requisição inválida: " + e.getMessage(), "requestId", id));
        } catch (Exception e) {
            status = 500;
            System.err.println("Falha interna " + id + ": " + e);
            resposta = Json.encode(Map.of("erro", "Erro interno", "requestId", id));
        }
        byte[] bytes = resposta.getBytes(StandardCharsets.UTF_8);
        try (exchange) {
            exchange.sendResponseHeaders(status, bytes.length);
            exchange.getResponseBody().write(bytes);
        }
    }

    public static void main(String[] args) throws IOException {
        String host = args.length > 0 ? args[0] : "127.0.0.1";
        int porta = args.length > 1 ? Integer.parseInt(args[1]) : 8080;
        Servidor app = new Servidor();
        HttpServer http = HttpServer.create(new InetSocketAddress(host, porta), 0);
        var pool = Executors.newFixedThreadPool(16);
        http.setExecutor(pool);
        http.createContext("/", app::atender);
        Runtime.getRuntime().addShutdownHook(new Thread(() -> { http.stop(0); pool.shutdownNow(); }));
        http.start();
        System.out.println("Biblioteca API pronta em http://" + host + ":" + http.getAddress().getPort());
    }
}
