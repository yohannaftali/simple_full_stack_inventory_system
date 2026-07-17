"""User repository for data access operations."""

from typing import Optional, Tuple
from sqlalchemy import Row

from core.table_query import (
    Pagination,
    apply_column_filters,
    apply_keyword_filter,
    apply_sort,
    paginate,
)
from models.base import SessionLocal
from models.department import DepartmentModel
from models.user import UserModel

_FILTER_COLUMN_MAP = {
    "username": UserModel.username,
    "email": UserModel.email,
    "is_active": UserModel.is_active,
    "is_superuser": UserModel.is_superuser,
    # Join-derived display column (looked up per-row by the router's own
    # _serialize_user(), not returned by this query) - outer-joined below
    # purely so it can be filtered/sorted.
    "department_name": DepartmentModel.name,
}


class UserRepository:
    """Repository class for user data access operations."""

    def get_user_by_username(self, username: str) -> Optional[UserModel]:
        """Get user by username."""
        with SessionLocal() as session:
            return (
                session.query(UserModel).filter(UserModel.username == username).first()
            )

    def get_user_by_email(self, email: str) -> Optional[UserModel]:
        """Get user by email."""
        with SessionLocal() as session:
            return session.query(UserModel).filter(UserModel.email == email).first()

    def check_user_exists(
        self, username: str, email: str, exclude_id: Optional[int] = None
    ) -> bool:
        """Check if user exists by username or email, optionally excluding one id
        (for update flows checking uniqueness against everyone else)."""
        with SessionLocal() as session:
            query = session.query(UserModel.id).filter(
                (UserModel.username == username) | (UserModel.email == email)
            )
            if exclude_id is not None:
                query = query.filter(UserModel.id != exclude_id)
            row: Row[Tuple[int]] | None = query.first()
            return row is not None

    def create_user(
        self,
        username: str,
        password: str,
        email: str,
        is_active: bool = True,
        is_superuser: bool = False,
        department_id: Optional[int] = None,
    ) -> UserModel:
        """Create a new user."""
        with SessionLocal() as session:
            user = UserModel(
                username=username,
                password=password,
                email=email,
                is_active=is_active,
                is_superuser=is_superuser,
                department_id=department_id,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    def update_user_password(self, username: str, new_password: str) -> bool:
        """Update user password."""
        with SessionLocal() as session:
            user = (
                session.query(UserModel).filter(UserModel.username == username).first()
            )
            if user is None:
                return False

            user.password = new_password
            session.commit()
            return True

    def update_user_totp_secret(self, username: str, totp_secret: str) -> bool:
        """Set (or clear, if empty) the user's TOTP secret."""
        with SessionLocal() as session:
            user = (
                session.query(UserModel).filter(UserModel.username == username).first()
            )
            if user is None:
                return False

            user.totp_secret = totp_secret
            session.commit()
            return True

    def get_user_count(self) -> int:
        """Get total number of users."""
        with SessionLocal() as session:
            return session.query(UserModel).count()

    def get_hashed_password(self, username: str) -> Optional[str]:
        """Get hashed password for a user."""
        with SessionLocal() as session:
            user = (
                session.query(UserModel).filter(UserModel.username == username).first()
            )
            if user is None:
                return None
            return user.password

    def delete_user(self, username: str) -> bool:
        """Delete a user by username."""
        with SessionLocal() as session:
            user = (
                session.query(UserModel).filter(UserModel.username == username).first()
            )
            if user is None:
                return False

            session.delete(user)
            session.commit()
            return True

    def update_user_status(self, username: str, is_active: bool) -> bool:
        """Update user active status."""
        with SessionLocal() as session:
            user = (
                session.query(UserModel).filter(UserModel.username == username).first()
            )
            if user is None:
                return False

            user.is_active = is_active
            session.commit()
            return True

    def make_superuser(self, username: str) -> bool:
        """Make user a superuser."""
        with SessionLocal() as session:
            user = (
                session.query(UserModel).filter(UserModel.username == username).first()
            )
            if user is None:
                return False

            user.is_superuser = True
            session.commit()
            return True

    def get_user_by_id(self, user_id: int) -> Optional[UserModel]:
        """Get user by id."""
        with SessionLocal() as session:
            return session.query(UserModel).filter(UserModel.id == user_id).first()

    def list_users(
        self,
        keyword: str = "",
        query_params=None,
        limit: int = 20,
        page: int = 1,
        offset: int = 0,
        sort_fields: list[tuple[str, str]] | None = None,
    ) -> tuple[list[UserModel], Pagination]:
        """List users matching an optional keyword, paginated."""
        with SessionLocal() as session:
            query = session.query(UserModel).outerjoin(
                DepartmentModel, DepartmentModel.id == UserModel.department_id
            )
            query = apply_keyword_filter(
                query, [UserModel.username, UserModel.email], keyword
            )
            if query_params is not None:
                query = apply_column_filters(query, query_params, _FILTER_COLUMN_MAP)
            if sort_fields:
                query = apply_sort(query, sort_fields, _FILTER_COLUMN_MAP)
            else:
                query = query.order_by(UserModel.username)
            return paginate(query, limit=limit, page=page, offset=offset, sort_fields=sort_fields)

    def update_user_by_id(
        self,
        user_id: int,
        username: str,
        email: str,
        is_active: bool,
        is_superuser: bool,
        password: Optional[str] = None,
        department_id: Optional[int] = None,
    ) -> bool:
        """Update a user's profile fields (admin CRUD path). Password only changes if given."""
        with SessionLocal() as session:
            user = session.query(UserModel).filter(UserModel.id == user_id).first()
            if user is None:
                return False

            user.username = username
            user.email = email
            user.is_active = is_active
            user.is_superuser = is_superuser
            user.department_id = department_id
            if password:
                user.password = password
            session.commit()
            return True

    def delete_user_by_id(self, user_id: int) -> bool:
        """Delete a user by id."""
        with SessionLocal() as session:
            user = session.query(UserModel).filter(UserModel.id == user_id).first()
            if user is None:
                return False

            session.delete(user)
            session.commit()
            return True
