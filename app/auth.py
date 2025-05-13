from asyncio.log import logger

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import Optional, Annotated
from sqlalchemy.orm import Session
from pydantic import EmailStr

from app import models, crud # Removed direct import of schemas, will use specific imports if needed or rely on what crud returns
from app.core.config import settings
from .database import get_db
# Import specific schemas that are used for type hinting or direct instantiation
from app.schemas.token_schemas import Token, TokenData # Corrected import
from app.schemas.usuario_schemas import UsuarioSchemas # Assuming UsuarioSchemas is the correct one for current_user

# Security configurations
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 schemes
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/token", # Adjusted to include API_V1_STR prefix
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
    ) -> Optional[models.Usuario]: # Assuming models.Usuario is the DB model
        """Authenticate a user with email and password."""
        user = crud.crud_usuario.get_by_email(db, email=email) # Adjusted to use crud_usuario
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
    ) -> models.Usuario: # Returns DB model
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

            email_from_payload: str = payload.get("sub")
            if email_from_payload is None:
                raise credentials_exception

            token_data_instance = TokenData(email=email_from_payload) # Using imported TokenData
        except JWTError:
            raise credentials_exception

        user = crud.crud_usuario.get_by_email(db, email=token_data_instance.email) # Adjusted
        if user is None:
            raise credentials_exception

        return user

    @staticmethod
    async def get_current_active_user(
            current_user: Annotated[models.Usuario, Depends(get_current_user)]
    ) -> models.Usuario: # Returns DB model
        """Get the current active user."""
        if not current_user.is_active: # Assuming DB model has is_active
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user"
            )
        return current_user

    @staticmethod
    async def get_current_active_admin(
            current_user: Annotated[models.Usuario, Depends(get_current_active_user)]
    ) -> models.Usuario: # Returns DB model
        """Get the current active admin user."""
        if current_user.cargo != "admin": # Assuming DB model has cargo
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        return current_user

    @staticmethod
    async def login_for_access_token(
            db: Session,
            form_data: OAuth2PasswordRequestForm
    ) -> Token: # Corrected return type to use imported Token
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
        return Token(
            access_token=access_token,
            refresh_token=refresh_token, # Token schema might need refresh_token field
            token_type="bearer"
        )

    @staticmethod
    async def refresh_access_token(
            db: Session,
            refresh_token: str
    ) -> Token: # Corrected return type
        """Generate a new access token from a refresh token."""
        try:
            payload = AuthService.decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )

            email_from_payload: str = payload.get("sub")
            if email_from_payload is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )

            user = crud.crud_usuario.get_by_email(db, email=email_from_payload) # Adjusted
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )

            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            new_access_token = AuthService.create_access_token(
                data={"sub": user.email},
                expires_delta=access_token_expires
            )
            # The Token schema might not have a refresh_token field when returning from refresh.
            # Adjusting to return only access_token and token_type as per typical refresh responses.
            return Token(
                access_token=new_access_token,
                token_type="bearer"
                # refresh_token field might not be part of this response, or it could be the same one if it's long-lived.
                # For simplicity, returning only new access token.
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )

