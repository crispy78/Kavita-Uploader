"""Kavita authentication service for user login and session management."""

import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Request
from itsdangerous import TimestampSigner, BadSignature

from app.config import config
from app.logger import app_logger


class KavitaAuthService:
    """Service for authenticating users with Kavita server."""
    
    def __init__(self):
        self.signer = TimestampSigner(config.auth.session_secret)
        self.kavita_url = config.kavita.server_url.rstrip('/')
        self.verify_ssl = config.kavita.verify_ssl
        self.timeout = config.kavita.timeout
    
    async def authenticate_with_kavita(
        self,
        username: str,
        password: str
    ) -> Dict[str, Any]:
        """Authenticate user with Kavita server using username/password.
        
        Based on Kavita API documentation:
        https://www.kavitareader.com/docs/api/#/
        
        Args:
            username: Kavita username
            password: Kavita password
            
        Returns:
            Dictionary with user information and token
            
        Raises:
            HTTPException: If authentication fails
        """
        if not config.kavita.enabled:
            raise HTTPException(
                status_code=400,
                detail="Kavita authentication is not enabled"
            )
        
        try:
            async with httpx.AsyncClient(verify=self.verify_ssl, timeout=self.timeout) as client:
                # Kavita login endpoint (typically /api/Account/login)
                login_url = f"{self.kavita_url}/api/Account/login"
                
                response = await client.post(
                    login_url,
                    json={
                        "username": username,
                        "password": password
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract user information from Kavita response
                    user_info = {
                        "username": username,
                        "token": data.get("token"),  # Kavita JWT token
                        "roles": data.get("roles", []),
                        "email": data.get("email"),
                        "id": data.get("id"),
                    }
                    
                    app_logger.info(
                        f"Kavita authentication successful",
                        extra={"username": username}
                    )
                    
                    return user_info
                elif response.status_code == 401:
                    app_logger.warning(
                        f"Kavita authentication failed - invalid credentials",
                        extra={"username": username}
                    )
                    raise HTTPException(
                        status_code=401,
                        detail="Invalid username or password"
                    )
                else:
                    app_logger.error(
                        f"Kavita authentication error: {response.status_code}",
                        extra={
                            "username": username,
                            "status_code": response.status_code,
                            "response": response.text[:200]
                        }
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=f"Kavita server error: {response.status_code}"
                    )
                    
        except httpx.TimeoutException:
            app_logger.error(
                f"Kavita authentication timeout",
                extra={"username": username, "timeout": self.timeout}
            )
            raise HTTPException(
                status_code=504,
                detail="Kavita server timeout"
            )
        except httpx.RequestError as e:
            app_logger.error(
                f"Kavita connection error: {str(e)}",
                extra={"username": username}
            )
            raise HTTPException(
                status_code=503,
                detail=f"Unable to connect to Kavita server: {str(e)}"
            )
    
    async def authenticate_with_api_key(
        self,
        api_key: str
    ) -> Dict[str, Any]:
        """Authenticate using Kavita API key.
        
        Args:
            api_key: Kavita API key
            
        Returns:
            Dictionary with user information
            
        Raises:
            HTTPException: If authentication fails
        """
        if not config.kavita.enabled:
            raise HTTPException(
                status_code=400,
                detail="Kavita authentication is not enabled"
            )
        
        try:
            async with httpx.AsyncClient(verify=self.verify_ssl, timeout=self.timeout) as client:
                # Validate API key with Kavita server
                # Typically /api/Account/validate-api-key or similar endpoint
                validate_url = f"{self.kavita_url}/api/Account/validate-api-key"
                
                response = await client.post(
                    validate_url,
                    json={"apiKey": api_key},
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    user_info = {
                        "username": data.get("username", "api_user"),
                        "token": api_key,
                        "roles": data.get("roles", []),
                        "email": data.get("email"),
                        "id": data.get("id"),
                        "api_key": True
                    }
                    
                    app_logger.info("Kavita API key authentication successful")
                    return user_info
                else:
                    raise HTTPException(
                        status_code=401,
                        detail="Invalid API key"
                    )
                    
        except httpx.RequestError as e:
            app_logger.error(f"Kavita API key validation error: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail=f"Unable to validate API key: {str(e)}"
            )
    
    def create_session_token(self, username: str, user_data: Dict[str, Any]) -> str:
        """Create a signed session token for the authenticated user.
        
        Args:
            username: Username
            user_data: Additional user data from Kavita
            
        Returns:
            Signed session token
        """
        import json
        
        token_data = {
            "username": username,
            "roles": user_data.get("roles", []),
            "email": user_data.get("email"),
            "user_id": user_data.get("id"),
            "exp": (datetime.utcnow() + timedelta(hours=config.auth.token_expiry_hours)).isoformat()
        }
        
        # Encode as JSON and sign
        json_data = json.dumps(token_data)
        token = self.signer.sign(json_data.encode('utf-8'))
        
        return token.decode('utf-8')
    
    def verify_session_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a session token.
        
        Args:
            token: Session token to verify
            
        Returns:
            User data dictionary or None if invalid
        """
        try:
            import json
            
            # Verify the signature and unsign
            data = self.signer.unsign(token, max_age=config.auth.token_expiry_hours * 3600)
            
            # Parse JSON data
            user_data = json.loads(data.decode('utf-8'))
            
            # Check expiry
            exp_str = user_data.get("exp")
            if exp_str:
                exp = datetime.fromisoformat(exp_str.replace('Z', '+00:00'))
                if exp < datetime.utcnow():
                    return None
            
            return user_data
            
        except (BadSignature, json.JSONDecodeError, ValueError, KeyError) as e:
            app_logger.debug(f"Token verification failed: {str(e)}")
            return None
        except Exception as e:
            app_logger.error(f"Token verification error: {str(e)}")
            return None
    
    def get_current_user(self, request: Request) -> Optional[Dict[str, Any]]:
        """Get current authenticated user from request.
        
        Checks for session token in cookie or Authorization header.
        
        Args:
            request: FastAPI request object
            
        Returns:
            User data dictionary or None if not authenticated
        """
        # Check cookie first
        token = request.cookies.get(config.auth.cookie_name)
        auth_header = None
        
        # If not in cookie, check Authorization header
        if not token:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header[7:]
        
        app_logger.debug(
            f"get_current_user token check",
            extra={
                "cookie_name": config.auth.cookie_name,
                "has_cookie_token": token is not None,
                "has_auth_header": bool(auth_header),
                "all_cookies": list(request.cookies.keys()),
            }
        )
        
        if not token:
            return None
        
        user_data = self.verify_session_token(token)
        
        app_logger.debug(
            f"get_current_user token verification",
            extra={
                "token_valid": user_data is not None,
                "username": user_data.get("username") if user_data else None,
            }
        )
        
        return user_data


# Global auth service instance
kavita_auth = KavitaAuthService()

