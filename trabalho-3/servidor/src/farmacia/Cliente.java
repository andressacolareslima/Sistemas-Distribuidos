package farmacia;
public final class Cliente extends Usuario {
    public Cliente(String nome) { super(nome); }
    public String getPerfil() { return "CLIENTE"; }
}
