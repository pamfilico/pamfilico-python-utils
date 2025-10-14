from sqlalchemy import BigInteger, Column, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID

from pamfilico_python_utils.sqlalchemy.utils import generate_uuid


class NextAuthUserMixin:
    """Mixin for NextAuth.js user table fields."""

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    email = Column(String(100), unique=True, nullable=True)
    image = Column(Text)
    emailVerified = Column(TIMESTAMP)
    name = Column(String(100), nullable=True)
    phone_number = Column(String(50), nullable=True)
    pin_number = Column(String(10), nullable=True)
    password_hash = Column(String(255), nullable=True)


class NextAuthVerificationTokenMixin:
    """Mixin for NextAuth.js verification token table fields."""

    identifier = Column(Text, primary_key=True)
    expires = Column(TIMESTAMP, nullable=False)
    token = Column(Text, primary_key=True)


class NextAuthSessionMixin:
    """Mixin for NextAuth.js session table fields."""

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    expires = Column(TIMESTAMP, nullable=False)
    sessionToken = Column(String(255), nullable=False)


class NextAuthAccountMixin:
    """Mixin for NextAuth.js account table fields."""

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    type = Column(String(255), nullable=False)
    provider = Column(String(255), nullable=False)
    provider_account_id = Column(String(255), nullable=False)
    refresh_token = Column(Text)
    access_token = Column(Text)
    expires_at = Column(BigInteger)
    id_token = Column(Text)
    scope = Column(Text)
    session_state = Column(Text)
    token_type = Column(Text)
