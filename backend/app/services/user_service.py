"""
User Service for TaxIA

Handles user CRUD operations with Turso database.
"""
import uuid
import logging
from typing import Optional
from datetime import datetime

from app.database.turso_client import get_db_client
from app.database.models import User, UserCreate, UserInDB
from app.auth.password import hash_password, verify_password

logger = logging.getLogger(__name__)


class UserService:
    """Service for user management operations."""
    
    async def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user.
        
        Args:
            user_data: User creation data
            
        Returns:
            Created user object
            
        Raises:
            ValueError: If email already exists
        """
        db = await get_db_client()
        
        # Check if email already exists
        existing = await self.get_user_by_email(user_data.email)
        if existing:
            raise ValueError("El email ya está registrado")
        
        user_id = str(uuid.uuid4())
        password_hash = hash_password(user_data.password)
        now = datetime.utcnow().isoformat()
        
        await db.execute(
            """
            INSERT INTO users (id, email, password_hash, name, is_active, is_admin, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [user_id, user_data.email, password_hash, user_data.name, True, False, now, now]
        )
        
        logger.info(f"Created user: {user_data.email}")
        
        return User(
            id=user_id,
            email=user_data.email,
            name=user_data.name,
            is_active=True,
            is_admin=False,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now)
        )
    
    async def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        """
        Get user by email.
        
        Args:
            email: User email
            
        Returns:
            User if found, None otherwise
        """
        db = await get_db_client()
        
        result = await db.execute(
            "SELECT * FROM users WHERE email = ?",
            [email]
        )
        
        if result.rows:
            row = result.rows[0]
            return UserInDB(
                id=row["id"],
                email=row["email"],
                password_hash=row["password_hash"],
                name=row["name"],
                is_active=bool(row["is_active"]),
                is_admin=bool(row["is_admin"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"])
            )
        
        return None
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User if found, None otherwise
        """
        db = await get_db_client()
        
        result = await db.execute(
            "SELECT * FROM users WHERE id = ?",
            [user_id]
        )
        
        if result.rows:
            row = result.rows[0]
            return User(
                id=row["id"],
                email=row["email"],
                name=row["name"],
                is_active=bool(row["is_active"]),
                is_admin=bool(row["is_admin"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"])
            )
        
        return None
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate user with email and password.
        
        Args:
            email: User email
            password: Plain text password
            
        Returns:
            User if authenticated, None otherwise
        """
        user = await self.get_user_by_email(email)
        
        if not user:
            logger.warning(f"Login attempt for non-existent user: {email}")
            return None
        
        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: {email}")
            return None
        
        if not verify_password(password, user.password_hash):
            logger.warning(f"Failed login attempt for user: {email}")
            return None
        
        logger.info(f"Successful login for user: {email}")
        
        return User(
            id=user.id,
            email=user.email,
            name=user.name,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
    
    async def update_user(self, user_id: str, **kwargs) -> Optional[User]:
        """
        Update user fields.
        
        Args:
            user_id: User ID
            **kwargs: Fields to update
            
        Returns:
            Updated user if found
        """
        db = await get_db_client()
        
        # Build update query
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in ["name", "email", "is_active"]:
                updates.append(f"{key} = ?")
                values.append(value)
        
        if not updates:
            return await self.get_user_by_id(user_id)
        
        updates.append("updated_at = ?")
        values.append(datetime.utcnow().isoformat())
        values.append(user_id)
        
        await db.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
            values
        )
        
        return await self.get_user_by_id(user_id)


# Global instance
user_service = UserService()
