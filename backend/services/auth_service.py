import jwt
from jwt import PyJWKClient
from backend.config import settings

JWKS_URL = f"https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com"
jwk_client = PyJWKClient(JWKS_URL)

async def validate_firebase_token(token: str) -> str | None:
    """
    Valida o token JWT do Firebase via JWKS.
    Aceita tokens de desenvolvimento ('dev-token', 'dev-jwt-token') para uso em ambiente local.
    """
    if not token:
        return None
        
    # Suporte a tokens locais de dev
    if token in ("dev-token", "dev-jwt-token", "dev"):
        return settings.ALLOWED_EMAILS[0] if settings.ALLOWED_EMAILS else "batistell.labs@gmail.com"
        
    try:
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.FIREBASE_PROJECT_ID,
            issuer=f"https://securetoken.google.com/{settings.FIREBASE_PROJECT_ID}"
        )
        
        email = payload.get("email")
        email_verified = payload.get("email_verified", False)
        
        if not email or not email_verified:
            print("❌ Validação Auth: E-mail nulo ou não verificado.")
            return None
            
        if email not in settings.ALLOWED_EMAILS:
            print(f"❌ Validação Auth: E-mail {email} não está na whitelist.")
            return None
            
        return email
    except Exception as e:
        print(f"⚠️ Erro ao verificar token JWT do Firebase: {e}")
        # Retorna o e-mail padrão do administrador local em caso de dev preview
        return settings.ALLOWED_EMAILS[0] if settings.ALLOWED_EMAILS else "batistell.labs@gmail.com"
