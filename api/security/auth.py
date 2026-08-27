# Copyright (c) 2026 Billiepy
# Licensed under the MIT License.
# This file is part of SiloHelper
import time
import logging
from fastapi import Security, HTTPException, status, Request
from fastapi.security import APIKeyQuery
from config.settings import settings

logger = logging.getLogger(__name__)

FAILED_ATTEMPT_LIMIT = 5
FAILED_ATTEMPT_WINDOW_SECONDS = 10
BAN_DURATION_SECONDS = 1800

failed_attempts = {}
banned_ips = {}

api_key_query = APIKeyQuery(name="api_key", auto_error=False)

def get_client_ip(request: Request) -> str:
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def verify_api_key(request: Request, api_key: str = Security(api_key_query)):
    ip = get_client_ip(request)
    now = time.time()

    if ip in banned_ips:
        if now < banned_ips[ip]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Too many invalid attempts. Try again later."
            )
        else:
            del banned_ips[ip]

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key is missing",
        )
        
    if api_key not in settings.valid_api_keys:
        if ip != "unknown":
            attempts = failed_attempts.get(ip, [])
            attempts = [ts for ts in attempts if now - ts < FAILED_ATTEMPT_WINDOW_SECONDS]
            attempts.append(now)
            failed_attempts[ip] = attempts
            
            if len(attempts) >= FAILED_ATTEMPT_LIMIT:
                banned_ips[ip] = now + BAN_DURATION_SECONDS
                if ip in failed_attempts:
                    del failed_attempts[ip]
                logger.warning(f"IP {ip} banned for repeated invalid API key attempts")
                
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key",
        )
        
    return api_key
