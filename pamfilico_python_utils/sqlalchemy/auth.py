from sqlalchemy import BigInteger, Boolean, Column, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID

from pamfilico_python_utils.sqlalchemy.utils import generate_uuid


class NextAuthUserMixin:
    """Mixin for NextAuth.js user table fields.

    Maps to NextAuth Prisma schema User model. Column names follow NextAuth
    conventions (camelCase where Prisma uses it) for compatibility.

    Prisma schema mapping:
        id -> id (UUID primary key)
        name -> name
        email -> email (unique)
        emailVerified -> emailVerified (DateTime, when verified)
        image -> image
        accounts, sessions, authenticators -> relations (app-defined)

    Optional columns (not in Prisma, used by some apps):
        email_verified: Boolean flag for quick checks (carfast-style)
        phone_number, pin_number, password_hash: credentials/contact
    """

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    email = Column(String(100), unique=True, nullable=True)
    image = Column(Text)
    emailVerified = Column(TIMESTAMP)
    name = Column(String(100), nullable=True)
    email_verified = Column(Boolean, default=False)
    phone_number = Column(String(50), nullable=True)
    pin_number = Column(String(10), nullable=True)
    password_hash = Column(String(255), nullable=True)


class NextAuthVerificationTokenMixin:
    """Mixin for NextAuth.js verification token table fields.

    Prisma schema mapping:
        identifier -> identifier (primary key)
        token -> token (primary key)
        expires -> expires (DateTime)
    """

    identifier = Column(Text, primary_key=True)
    expires = Column(TIMESTAMP, nullable=False)
    token = Column(Text, primary_key=True)


class NextAuthSessionMixin:
    """Mixin for NextAuth.js session table fields.

    Prisma schema mapping:
        sessionToken -> sessionToken (camelCase, unique)
        userId -> user_id (snake_case for SQLAlchemy FK convention)
        expires -> expires (DateTime)
        user -> relation (app-defined)
    """

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    expires = Column(TIMESTAMP, nullable=False)
    sessionToken = Column(String(255), nullable=False)


class NextAuthAccountMixin:
    """Mixin for NextAuth.js account table fields.

    Prisma schema mapping:
        userId -> user_id (app adds FK; Prisma uses camelCase userId)
        providerAccountId -> provider_account_id (snake_case; Prisma camelCase)
        type, provider, refresh_token, access_token, expires_at, etc. -> same
    """

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
