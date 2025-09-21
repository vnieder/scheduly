"""
Auth0 JWT validation middleware for FastAPI.
"""

import jwt
import requests
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class Auth0Service:
    """Service for Auth0 JWT validation and user management."""
    
    def __init__(self, domain: str, audience: str):
        self.domain = domain
        self.audience = audience
        self.jwks_url = f"https://{domain}/.well-known/jwks.json"
        self._jwks_cache = None
    
    def get_jwks(self) -> Dict[str, Any]:
        """Get JSON Web Key Set from Auth0."""
        if self._jwks_cache is None:
            try:
                response = requests.get(self.jwks_url)
                response.raise_for_status()
                self._jwks_cache = response.json()
            except Exception as e:
                logger.error(f"Failed to fetch JWKS: {e}")
                raise HTTPException(status_code=503, detail="Authentication service unavailable")
        
        return self._jwks_cache
    
    def get_signing_key(self, token: str) -> str:
        """Get the signing key for the JWT token."""
        try:
            # Decode header to get key ID
            header = jwt.get_unverified_header(token)
            kid = header.get('kid')
            
            if not kid:
                raise HTTPException(status_code=401, detail="Invalid token header")
            
            # Get JWKS and find the key
            jwks = self.get_jwks()
            for key in jwks.get('keys', []):
                if key.get('kid') == kid:
                    # Convert JWK to PEM format
                    from cryptography.hazmat.primitives import serialization
                    from cryptography.hazmat.primitives.asymmetric import rsa
                    import base64
                    
                    # This is a simplified version - in production, use a proper JWK library
                    return self._convert_jwk_to_pem(key)
            
            raise HTTPException(status_code=401, detail="Unable to find appropriate key")
            
        except Exception as e:
            logger.error(f"Error getting signing key: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")
    
    def _convert_jwk_to_pem(self, jwk: Dict[str, Any]) -> str:
        """Convert JWK to PEM format (simplified implementation)."""
        # This is a simplified implementation
        # In production, use a proper JWK library like PyJWT with cryptography
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            import base64
            
            # Extract RSA components
            n = base64.urlsafe_b64decode(jwk['n'] + '==')
            e = base64.urlsafe_b64decode(jwk['e'] + '==')
            
            # Convert to integers
            n_int = int.from_bytes(n, 'big')
            e_int = int.from_bytes(e, 'big')
            
            # Create RSA public key
            public_key = rsa.RSAPublicNumbers(e_int, n_int).public_key()
            
            # Convert to PEM
            pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            return pem.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error converting JWK to PEM: {e}")
            raise HTTPException(status_code=401, detail="Invalid key format")
    
    def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate JWT token and return payload."""
        try:
            # Get signing key
            signing_key = self.get_signing_key(token)
            
            # Decode and validate token
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=['RS256'],
                audience=self.audience,
                issuer=f"https://{self.domain}/"
            )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise HTTPException(status_code=401, detail="Token validation failed")

# Global Auth0 service instance
auth0_service = None

def get_auth0_service() -> Auth0Service:
    """Get Auth0 service instance."""
    global auth0_service
    if auth0_service is None:
        import os
        domain = os.getenv("AUTH0_DOMAIN")
        audience = os.getenv("AUTH0_AUDIENCE")
        
        if not domain or not audience:
            raise HTTPException(status_code=500, detail="Auth0 configuration missing")
        
        auth0_service = Auth0Service(domain, audience)
    
    return auth0_service

# Security scheme
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current authenticated user from JWT token."""
    try:
        auth0 = get_auth0_service()
        payload = auth0.validate_token(credentials.credentials)
        
        # Extract user information from token
        user_info = {
            "sub": payload.get("sub"),
            "email": payload.get("email"),
            "name": payload.get("name"),
            "picture": payload.get("picture"),
            "aud": payload.get("aud"),
            "iss": payload.get("iss")
        }
        
        return user_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

def get_optional_user(request: Request) -> Optional[Dict[str, Any]]:
    """Get current user if authenticated, otherwise return None."""
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.split(" ")[1]
        auth0 = get_auth0_service()
        payload = auth0.validate_token(token)
        
        return {
            "sub": payload.get("sub"),
            "email": payload.get("email"),
            "name": payload.get("name"),
            "picture": payload.get("picture"),
            "aud": payload.get("aud"),
            "iss": payload.get("iss")
        }
        
    except Exception:
        return None

