from datetime import datetime
from database.db import db


class ChatMessage(db.Model):
    """Academic chatbot conversation message."""

    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="chat_messages")

    def to_dict(self):
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.strftime("%H:%M")
            if self.created_at
            else "",
        }

    def __repr__(self):
        return f"<ChatMessage User {self.user_id} Role {self.role}>"
