import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.core.config import settings

security = HTTPBearer()

def get_jwks_url() -> str:
    base_url = settings.supabase_url.rstrip("/")
    if not base_url:
        raise ValueError("SUPABASE_URL environment variable is not set")
    return f"{base_url}/auth/v1/.well-known/jwks.json"

# Initialize the JWK client
try:
    jwks_client = PyJWKClient(get_jwks_url())
except ValueError:
    jwks_client = None


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Validates the JWT token using Supabase's JWKS endpoint.
    Returns the user_id (sub claim) if valid.
    """
    if not jwks_client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase URL is not configured properly."
        )

    token = credentials.credentials
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        # Audience and Issuer based on Supabase documentation and user spec
        base_url = settings.supabase_url.rstrip("/")
        expected_issuer = f"{base_url}/auth/v1"

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience="authenticated",
            issuer=expected_issuer,
            leeway=60,
            options={"verify_exp": True}
        )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing subject claim"
            )

        return user_id

    except jwt.PyJWKClientError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unable to fetch signing key: {str(e)}"
        ) from e
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        ) from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        ) from e
