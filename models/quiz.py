import json
from datetime import datetime
from database.db import db


class Quiz(db.Model):
    """Quiz container model."""

    __tablename__ = "quizzes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    document_id = db.Column(
        db.Integer, db.ForeignKey("documents.id"), nullable=True, index=True
    )
    title = db.Column(db.String(200), nullable=False)
    topic = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship("User", back_populates="quizzes")
    document = db.relationship("Document", back_populates="quizzes")
    questions = db.relationship(
        "QuizQuestion",
        back_populates="quiz",
        cascade="all, delete-orphan",
        lazy="select",
    )
    attempts = db.relationship(
        "QuizAttempt",
        back_populates="quiz",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="desc(QuizAttempt.attempted_at)",
    )

    def to_dict(self, include_questions=False, hide_answers=True):
        data = {
            "id": self.id,
            "title": self.title,
            "topic": self.topic,
            "document_id": self.document_id,
            "document_name": self.document.filename if self.document else None,
            "question_count": len(self.questions),
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M")
            if self.created_at
            else "",
            "latest_score": self.attempts[0].score if self.attempts else None,
            "attempts_count": len(self.attempts),
        }
        if include_questions:
            data["questions"] = [
                q.to_dict(hide_answer=hide_answers) for q in self.questions
            ]
        return data

    def __repr__(self):
        return f"<Quiz {self.title} (Topic: {self.topic})>"


class QuizQuestion(db.Model):
    """Individual Multiple-Choice Question."""

    __tablename__ = "quiz_questions"

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(
        db.Integer, db.ForeignKey("quizzes.id"), nullable=False, index=True
    )
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(255), nullable=False)
    option_b = db.Column(db.String(255), nullable=False)
    option_c = db.Column(db.String(255), nullable=False)
    option_d = db.Column(db.String(255), nullable=False)
    correct_option = db.Column(db.String(1), nullable=False)  # 'A', 'B', 'C', or 'D'
    explanation = db.Column(db.Text, nullable=True)

    quiz = db.relationship("Quiz", back_populates="questions")

    def to_dict(self, hide_answer=True):
        """Serialize question. Hides correct answer when student is taking the quiz."""
        data = {
            "id": self.id,
            "question_text": self.question_text,
            "options": {
                "A": self.option_a,
                "B": self.option_b,
                "C": self.option_c,
                "D": self.option_d,
            },
        }
        if not hide_answer:
            data["correct_option"] = self.correct_option
            data["explanation"] = self.explanation
        return data

    def __repr__(self):
        return f"<QuizQuestion {self.id} for Quiz {self.quiz_id}>"


class QuizAttempt(db.Model):
    """Quiz submission record for performance tracking."""

    __tablename__ = "quiz_attempts"

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(
        db.Integer, db.ForeignKey("quizzes.id"), nullable=False, index=True
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    score = db.Column(db.Float, nullable=False)  # percentage (0.0 to 100.0)
    total_questions = db.Column(db.Integer, nullable=False)
    correct_answers = db.Column(db.Integer, nullable=False)
    user_answers_json = db.Column(
        db.Text, nullable=False
    )  # JSON-encoded array of review details
    attempted_at = db.Column(db.DateTime, default=datetime.utcnow)

    quiz = db.relationship("Quiz", back_populates="attempts")
    user = db.relationship("User", back_populates="quiz_attempts")

    def get_details(self):
        try:
            return json.loads(self.user_answers_json)
        except Exception:
            return []

    def to_dict(self):
        return {
            "id": self.id,
            "quiz_id": self.quiz_id,
            "quiz_title": self.quiz.title if self.quiz else "Quiz",
            "topic": self.quiz.topic if self.quiz else "General",
            "score": round(self.score, 1),
            "total_questions": self.total_questions,
            "correct_answers": self.correct_answers,
            "details": self.get_details(),
            "attempted_at": self.attempted_at.strftime("%Y-%m-%d %H:%M")
            if self.attempted_at
            else "",
        }

    def __repr__(self):
        return f"<QuizAttempt {self.id} Quiz {self.quiz_id} Score: {self.score}%>"
