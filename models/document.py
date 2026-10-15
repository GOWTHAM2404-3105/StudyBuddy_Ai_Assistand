import json
from datetime import datetime
from database.db import db


class Document(db.Model):
    """Uploaded PDF notes model."""

    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False, unique=True)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False, default=0)
    page_count = db.Column(db.Integer, nullable=False, default=0)

    # Extracted content & AI metadata
    extracted_text = db.Column(db.Text, nullable=True)
    summary = db.Column(db.Text, nullable=True)
    key_points = db.Column(db.Text, nullable=True)  # JSON-encoded list of strings
    chunks_json = db.Column(
        db.Text, nullable=True
    )  # JSON-encoded list of chunk dicts {id, text, page}

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship("User", back_populates="documents")
    quizzes = db.relationship("Quiz", back_populates="document", lazy="select")

    def get_chunks(self):
        """Return parsed chunks list."""
        if not self.chunks_json:
            return []
        try:
            return json.loads(self.chunks_json)
        except Exception:
            return []

    def set_chunks(self, chunks):
        """Store list of chunk dicts as JSON."""
        self.chunks_json = json.dumps(chunks)

    def get_key_points(self):
        """Return parsed key points list."""
        if not self.key_points:
            return []
        try:
            return json.loads(self.key_points)
        except Exception:
            return [line.strip() for line in self.key_points.split("\n") if line.strip()]

    def set_key_points(self, points):
        """Store key points list as JSON."""
        if isinstance(points, list):
            self.key_points = json.dumps(points)
        else:
            self.key_points = json.dumps([str(points)])

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "file_size": self.file_size,
            "page_count": self.page_count,
            "summary": self.summary,
            "key_points": self.get_key_points(),
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M")
            if self.created_at
            else "",
        }

    def __repr__(self):
        return f"<Document {self.filename} (User {self.user_id})>"
