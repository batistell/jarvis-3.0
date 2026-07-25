# ADR-008: Autenticação via Firebase (Google Sign-In) e Restrição de E-mail em Python

## Status
Aceito

## Contexto
Como o Jarvis 3.0 controla dispositivos físicos na casa e armazena histórico de conversas sensíveis, a aplicação exige uma camada de segurança robusta baseada em provedor de identidade confiável (Google via Firebase Auth) com autorização restrita por lista de e-mails (whitelist).

## Decisão
Implementamos a validação de segurança no FastAPI utilizando as bibliotecas **`PyJWT`** e **`cryptography`**, consultando dinamicamente o JWKS público da Google (`https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com`).

### Regras de Validação:
1. **Assinatura Criptográfica**: Verificada usando a chave pública do Google identificada pelo `kid` no cabeçalho do JWT.
2. **Issuer & Audience**: `iss` deve ser `https://securetoken.google.com/jarvis-1006b` e `aud` deve ser `jarvis-1006b`.
3. **Email Whitelist**: O e-mail contido no token JWT deve ter `email_verified == true` e constar na variável de ambiente `ALLOWED_EMAILS` (ex: `batistell.labs@gmail.com`).

## Consequências
* **Positivas**:
  * Não há necessidade de armazenar senhas ou chaves privadas do Firebase Admin SDK na máquina local.
  * Validação puramente criptográfica e descentralizada.
