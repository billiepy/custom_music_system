from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyQuery
from config.settings import settings

api_key_query = APIKeyQuery(name="api_key", auto_error=False)

def verify_api_key(api_key: str = Security(api_key_query)):
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key is missing",
        )
    if api_key not in settings.valid_api_keys:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key",
        )
    return api_key
