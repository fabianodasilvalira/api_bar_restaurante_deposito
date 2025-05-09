from asyncio.log import logger

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import Optional, Annotated
from sqlalchemy.orm import Session
from pydantic import EmailStr

from . import schemas, models, crud
from app.core.config import settings
from .database import get_db

# Security configurations
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 schemes
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/token",
    scopes={
        "admin": "Administrator access",
        "manager": "Manager access",
        "waiter": "Waiter access",
        "cashier": "Cashier access"
    }
)


class AuthService:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Generate a password hash."""
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(
            data: dict,
            expires_delta: Optional[timedelta] = None
    ) -> str:
        """Cria um token JWT de acesso."""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (
            expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    @staticmethod
    def create_refresh_token(
            data: dict,
            expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT refresh token."""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (
            expires_delta if expires_delta
            else timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    @staticmethod
    def decode_token(token: str) -> dict:
        """Decode a JWT token."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError as e:
            logger.error(f"Token decode error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @staticmethod
    async def authenticate_user(
            db: Session,
            email: EmailStr,
            password: str
    ) -> Optional[models.Usuario]:
        """Authenticate a user with email and password."""
        user = crud.get_user_by_email(db, email)
        if not user:
            logger.warning(f"Login attempt with non-existent email: {email}")
            return None
        if not AuthService.verify_password(password, user.hashed_password):
            logger.warning(f"Invalid password attempt for user: {email}")
            return None
        return user

    @staticmethod
    async def get_current_user(
            token: Annotated[str, Depends(oauth2_scheme)],
            db: Annotated[Session, Depends(get_db)]
    ) -> models.Usuario:
        """Get the current authenticated user from the token."""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            payload = AuthService.decode_token(token)
            if payload.get("type") != "access":
                raise credentials_exception

            email: str = payload.get("sub")
            if email is None:
                raise credentials_exception

            token_data = schemas.TokenData(email=email)
        except JWTError:
            raise credentials_exception

        user = crud.get_user_by_email(db, email=token_data.email)
        if user is None:
            raise credentials_exception

        return user

    @staticmethod
    async def get_current_active_user(
            current_user: Annotated[models.Usuario, Depends(get_current_user)]
    ) -> models.Usuario:
        """Get the current active user."""
        if not current_user.ativo:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user"
            )
        return current_user

    @staticmethod
    async def get_current_active_admin(
            current_user: Annotated[models.Usuario, Depends(get_current_active_user)]
    ) -> models.Usuario:
        """Get the current active admin user."""
        if current_user.cargo != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        return current_user

    @staticmethod
    async def login_for_access_token(
            db: Session,
            form_data: OAuth2PasswordRequestForm
    ) -> schemas.TokenSchemas:
        """Generate access and refresh tokens for valid credentials."""
        user = await AuthService.authenticate_user(
            db, form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = AuthService.create_access_token(
            data={"sub": user.email, "scopes": form_data.scopes},
            expires_delta=access_token_expires
        )

        refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = AuthService.create_refresh_token(
            data={"sub": user.email},
            expires_delta=refresh_token_expires
        )

        logger.info(f"User {user.email} logged in successfully")
        return schemas.Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )

    @staticmethod
    async def refresh_access_token(
            db: Session,
            refresh_token: str
    ) -> schemas.TokenSchemas:
        """Generate a new access token from a refresh token."""
        try:
            payload = AuthService.decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )

            email: str = payload.get("sub")
            if email is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )

            user = crud.get_user_by_email(db, email=email)
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )

            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = AuthService.create_access_token(
                data={"sub": user.email},
                expires_delta=access_token_expires
            )

            return schemas.Token(
                access_token=access_token,
                token_type="bearer"
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )