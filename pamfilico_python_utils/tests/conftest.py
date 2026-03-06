"""
Shared pytest fixtures for pamfilico-python-utils tests.
"""
from datetime import date, datetime

import pytest
from flask import Flask
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class Item(Base):
    """Test model for filtering tests."""

    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    status = Column(String(50))
    category = Column(String(50))
    price = Column(Float)
    quantity = Column(Integer)
    is_active = Column(Boolean)
    created_date = Column(Date)
    created_at = Column(DateTime)


# --- Generic Flask app ---


@pytest.fixture
def flask_app():
    """Minimal Flask app for testing."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


# --- Mock DB session (for user_auth tests) ---


@pytest.fixture
def mock_db_session():
    """Mock SQLAlchemy-like session for init_user_auth tests."""

    class Session:
        def query(self, m):
            return self

        def filter(self, *a):
            return self

        def filter_by(self, **k):
            return self

        def first(self):
            return None

        def get(self, x):
            return None

        def add(self, x):
            pass

        def commit(self):
            pass

        def rollback(self):
            pass

        def delete(self, x):
            pass

        def close(self):
            pass

    return Session


# --- Filtering fixtures (SQLite + Item model) ---


@pytest.fixture(scope="session")
def filter_app():
    """Flask app for filtering tests."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


@pytest.fixture(scope="session")
def filter_engine():
    return create_engine("sqlite:///:memory:")


@pytest.fixture(scope="session")
def filter_tables(filter_engine):
    Base.metadata.create_all(filter_engine)
    yield
    Base.metadata.drop_all(filter_engine)


@pytest.fixture(scope="session")
def filter_Session(filter_engine, filter_tables):
    return sessionmaker(bind=filter_engine)


@pytest.fixture(scope="session")
def filter_seed_data(filter_Session):
    session = filter_Session()
    items = [
        Item(
            id=1,
            name="Gaming Laptop",
            status="active",
            category="electronics",
            price=1200.0,
            quantity=5,
            is_active=True,
            created_date=date(2025, 1, 15),
            created_at=datetime(2025, 1, 15, 10, 30),
        ),
        Item(
            id=2,
            name="Office Laptop",
            status="active",
            category="electronics",
            price=800.0,
            quantity=10,
            is_active=True,
            created_date=date(2025, 2, 20),
            created_at=datetime(2025, 2, 20, 14, 0),
        ),
        Item(
            id=3,
            name="Wireless Mouse",
            status="active",
            category="accessories",
            price=25.0,
            quantity=100,
            is_active=True,
            created_date=date(2025, 3, 1),
            created_at=datetime(2025, 3, 1, 9, 0),
        ),
        Item(
            id=4,
            name="Mechanical Keyboard",
            status="pending",
            category="accessories",
            price=150.0,
            quantity=30,
            is_active=True,
            created_date=date(2025, 3, 10),
            created_at=datetime(2025, 3, 10, 16, 45),
        ),
        Item(
            id=5,
            name="Broken Monitor",
            status="deleted",
            category="electronics",
            price=300.0,
            quantity=0,
            is_active=False,
            created_date=date(2024, 12, 1),
            created_at=datetime(2024, 12, 1, 8, 0),
        ),
    ]
    session.add_all(items)
    session.commit()
    session.close()


@pytest.fixture
def filter_session(filter_Session, filter_seed_data):
    s = filter_Session()
    yield s
    s.close()
