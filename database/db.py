from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy instance
db = SQLAlchemy()

def init_db(app):
    """Initialize database and create all tables within app context."""
    db.init_app(app)
    with app.app_context():
        # Import models so SQLAlchemy registers tables before create_all
        import models  # noqa: F401
        db.create_all()
