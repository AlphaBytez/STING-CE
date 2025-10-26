"""
Database models for STING application.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from contextlib import contextmanager
import os

db = SQLAlchemy()
migrate = Migrate()

# Create async session maker
async_session = None

def init_db(app):
    global async_session
    
    # Initialize regular SQLAlchemy
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Initialize async engine
    database_url = app.config['SQLALCHEMY_DATABASE_URI']
    if database_url.startswith('postgresql://'):
        async_database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://')
    else:
        async_database_url = database_url
        
    async_engine = create_async_engine(
        async_database_url,
        echo=app.config.get('SQLALCHEMY_ECHO', False),
    )
    
    # Create async session maker
    async_session = sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    # Create tables
    with app.app_context():
        db.create_all()
        db.session.commit()
    
    print("Database initialized with async support.")

async def get_async_session():
    """Get an async database session."""
    if async_session is None:
        raise RuntimeError("Database not initialized. Call init_db first.")
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

@contextmanager
def get_db_session():
    """Context manager for synchronous database sessions."""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
    
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()