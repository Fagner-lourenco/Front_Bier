"""
Utilitários de segurança
- Validação HMAC para tokens do APP
"""
import hmac
import hashlib
import base64
import json
from typing import Optional
from datetime import datetime


def verify_hmac_signature(payload: str, signature: str, secret: str) -> bool:
    """
    Verifica assinatura HMAC-SHA256
    
    Args:
        payload: String do payload (JSON stringificado)
        signature: Assinatura a verificar
        secret: Chave HMAC compartilhada
    
    Returns:
        True se assinatura válida
    """
    try:
        expected = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected, signature)
    except Exception:
        return False


def decode_token_payload(token_b64: str) -> Optional[dict]:
    """
    Decodifica payload base64 do token local
    
    Args:
        token_b64: Token em base64
    
    Returns:
        Dict com payload ou None se inválido
    """
    try:
        payload_json = base64.b64decode(token_b64).decode('utf-8')
        return json.loads(payload_json)
    except Exception:
        return None


def is_token_expired(expires_at: str) -> bool:
    """
    Verifica se token expirou
    
    Args:
        expires_at: ISO timestamp de expiração
    
    Returns:
        True se expirado
    """
    try:
        expiry = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        return datetime.utcnow().replace(tzinfo=expiry.tzinfo) > expiry
    except Exception:
        return True


def generate_hmac_signature(payload: str, secret: str) -> str:
    """
    Gera assinatura HMAC-SHA256
    
    Args:
        payload: String do payload (JSON stringificado)
        secret: Chave HMAC
    
    Returns:
        Assinatura hexadecimal
    """
    return hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
