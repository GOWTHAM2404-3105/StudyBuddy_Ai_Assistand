from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import db


class User(db.Model):
    """Student user account model."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    documents = db.relationship(
        "Document",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )
    quizzes = db.relationship(
        "Quiz",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )
    quiz_attempts = db.relationship(
        "QuizAttempt",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )
    predictions = db.relationship(
        "StudentPrediction",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )
    chat_messages = db.relationship(
        "ChatMessage",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def set_password(self, password: str):
        """Hash and store the password securely."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify the password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """Serialize user object to dictionary (excluding sensitive password)."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name or self.username,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<User {self.username}>"
