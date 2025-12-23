"""
Utilitários de autenticação
- JWT para usuários admin (dashboard)
- API Key para máquinas (APP Kiosk)
"""
from datetime import datetime, timedelta
from typing import Optional, Annotated

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import bcrypt
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import User, Machine

# OAuth2 scheme para JWT
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login", auto_error=False)


def get_password_hash(password: str) -> str:
    """Gera hash da senha usando bcrypt"""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha está correta"""
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Cria token JWT"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """Decodifica token JWT"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None


async def get_current_user(
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency: obtém usuário atual via JWT
    Usado para rotas admin (dashboard)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception
    
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive"
        )
    
    return user


async def get_current_user_optional(
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Dependency: obtém usuário atual (opcional)
    Retorna None se não autenticado
    """
    if not token:
        return None
    
    payload = decode_token(token)
    if payload is None:
        return None
    
    user_id: str = payload.get("sub")
    if user_id is None:
        return None
    
    user = db.query(User).filter(User.id == user_id, User.active == True).first()
    return user


async def get_machine_by_api_key(
    x_api_key: Annotated[Optional[str], Header(alias="X-API-Key")] = None,
    db: Session = Depends(get_db)
) -> Machine:
    """
    Dependency: obtém máquina via API Key
    Usado para rotas do APP Kiosk
    Header: X-API-Key: sk_xxxxx
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key required",
            headers={"X-API-Key": "Required"},
        )
    
    machine = db.query(Machine).filter(
        Machine.api_key == x_api_key,
        Machine.active == True
    ).first()
    
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    
    return machine


async def get_machine_optional(
    x_api_key: Annotated[Optional[str], Header(alias="X-API-Key")] = None,
    db: Session = Depends(get_db)
) -> Optional[Machine]:
    """
    Dependency: obtém máquina via API Key (opcional)
    Retorna None se não autenticado
    """
    if not x_api_key:
        return None
    
    machine = db.query(Machine).filter(
        Machine.api_key == x_api_key,
        Machine.active == True
    ).first()
    
    return machine
