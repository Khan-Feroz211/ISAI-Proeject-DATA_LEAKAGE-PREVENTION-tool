"""
database.py – SQLAlchemy setup + helper to create all tables.
Import `db` from here throughout the application.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()


def init_db(app):
    """Bind Flask-SQLAlchemy and Flask-Migrate to `app`."""
    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        db.create_all()
