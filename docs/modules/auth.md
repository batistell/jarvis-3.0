# Módulo de Autenticação (Auth Domain)

Este módulo é responsável por garantir a segurança e autenticidade de toda conexão que chega ao Jarvis 3.0 no backend FastAPI.

---

## 1. Responsabilidade

Validar o ID Token (JWT) do Firebase Authentication fornecido pelo frontend contra as chaves públicas vigentes publicadas no JWKS do Google. A validação ocorre durante o handshake inicial dos WebSockets em `/ws/voice?token=...` ou no cabeçalho `Authorization: Bearer <TOKEN>` de requisições REST.

---

## 2. Fluxo de Validação Criptográfica em Python

O backend Python atua como um servidor de recursos OAuth2/JWT autossuficiente (sem necessidade de arquivos de chave de serviço `serviceAccountKey.json`). Ele realiza a verificação usando a biblioteca `PyJWT` e as chaves públicas do Google:

1. **Leitura do Key ID (`kid`)**: O backend decodifica o cabeçalho do token JWT fornecido pelo cliente e extrai o campo `kid`.
2. **Consulta ao JWKS público**: O backend obtém as chaves criptográficas ativas na URL oficial do Google:
   `https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com`
3. **Verificação de Assinatura**: A assinatura digital RS256 do token é verificada usando a chave correspondente ao `kid`.
4. **Verificação de Claims**:
   * **Issuer (`iss`)**: Deve ser exatamente `https://securetoken.google.com/jarvis-1006b`.
   * **Audience (`aud`)**: Deve ser exatamente `jarvis-1006b` (o ID do projeto Firebase).
   * **Expiração (`exp`)**: Deve ser maior que o timestamp atual.
   * **Verificação de E-mail (`email_verified`)**: Deve ser `true`.

---

## 3. Autorização (Whitelist de E-mails)

Após a decodificação bem-sucedida do token, a função de autorização extrai o e-mail do usuário da claim `email`. O acesso é permitido somente se o e-mail estiver na whitelist configurada no arquivo `.env` (ex: `ALLOWED_EMAILS=batistell.labs@gmail.com`).

Caso o e-mail não esteja autorizado, o FastAPI lança uma exceção `HTTP 403 Forbidden` em rotas REST ou fecha a conexão WebSocket imediatamente com o código de encerramento `1008 (WS_1008_POLICY_VIOLATION)`.
