"""
Keycloak OIDC Authentication Service
Validates Keycloak access tokens and extracts user claims
"""
import httpx
from jose import jwt, JWTError
from jose.exceptions import JWKError
from typing import Optional, Dict, Any
from functools import lru_cache
import time

from config import settings


class KeycloakService:
    """Service for Keycloak OIDC token validation"""
    
    def __init__(self):
        self.server_url = settings.KEYCLOAK_SERVER_URL
        self.realm = settings.KEYCLOAK_REALM
        self.client_id = settings.KEYCLOAK_CLIENT_ID
        self.client_secret = settings.KEYCLOAK_CLIENT_SECRET
        self._jwks_cache: Optional[Dict] = None
        self._jwks_cache_time: float = 0
        self._oidc_config_cache: Optional[Dict] = None
    
    @property
    def oidc_config_url(self) -> str:
        return f"{self.server_url}/realms/{self.realm}/.well-known/openid-configuration"
    
    @property
    def issuer(self) -> str:
        return f"{self.server_url}/realms/{self.realm}"
    
    async def get_oidc_config(self) -> Dict:
        """Get OIDC configuration from Keycloak"""
        if self._oidc_config_cache:
            return self._oidc_config_cache
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.oidc_config_url, timeout=10.0)
            response.raise_for_status()
            self._oidc_config_cache = response.json()
            return self._oidc_config_cache
    
    async def get_jwks(self) -> Dict:
        """Get JSON Web Key Set from Keycloak"""
        # Cache JWKS for 1 hour
        if self._jwks_cache and (time.time() - self._jwks_cache_time) < 3600:
            return self._jwks_cache
        
        try:
            oidc_config = await self.get_oidc_config()
            jwks_uri = oidc_config.get("jwks_uri")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(jwks_uri, timeout=10.0)
                response.raise_for_status()
                self._jwks_cache = response.json()
                self._jwks_cache_time = time.time()
                return self._jwks_cache
        except Exception as e:
            print(f"Error fetching JWKS: {e}")
            raise
    
    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate Keycloak access token and return claims.
        Returns None if token is invalid.
        """
        try:
            # Get JWKS for signature verification
            jwks = await self.get_jwks()
            
            # Decode header to get key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            # Find matching key
            rsa_key = None
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    rsa_key = key
                    break
            
            if not rsa_key:
                print(f"No matching key found for kid: {kid}")
                return None
            
            # Verify and decode token
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.issuer,
                options={"verify_aud": True, "verify_iss": True}
            )
            
            return payload
            
        except JWTError as e:
            print(f"JWT validation error: {e}")
            return None
        except JWKError as e:
            print(f"JWK error: {e}")
            return None
        except Exception as e:
            print(f"Token validation error: {e}")
            return None
    
    def extract_user_info(self, token_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract user information from token claims"""
        return {
            "sub": token_payload.get("sub"),  # Keycloak user ID
            "email": token_payload.get("email"),
            "email_verified": token_payload.get("email_verified", False),
            "preferred_username": token_payload.get("preferred_username"),
            "name": token_payload.get("name"),
            "given_name": token_payload.get("given_name"),
            "family_name": token_payload.get("family_name"),
            "roles": token_payload.get("roles", []),
            "groups": token_payload.get("groups", []),
        }
    
    def is_keycloak_token(self, token: str) -> bool:
        """Check if token appears to be a Keycloak token (RS256 algorithm)"""
        try:
            header = jwt.get_unverified_header(token)
            return header.get("alg") == "RS256"
        except:
            return False


# Singleton instance
_keycloak_service: Optional[KeycloakService] = None


def get_keycloak_service() -> KeycloakService:
    """Get singleton KeycloakService instance"""
    global _keycloak_service
    if _keycloak_service is None:
        _keycloak_service = KeycloakService()
    return _keycloak_service
