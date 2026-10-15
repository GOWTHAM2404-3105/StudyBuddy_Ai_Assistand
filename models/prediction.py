import json
from datetime import datetime
from database.db import db


class StudentPrediction(db.Model):
    """Student academic performance prediction record."""

    __tablename__ = "student_predictions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )

    # Core features from UCI dataset
    studytime = db.Column(db.Integer, nullable=False)  # 1 to 4 scale
    failures = db.Column(db.Integer, nullable=False)  # 0 to 4
    absences = db.Column(db.Integer, nullable=False)  # 0 to 93

    # Optional extra features
    extra_features_json = db.Column(db.Text, nullable=True)

    # Output prediction
    predicted_grade = db.Column(db.Float, nullable=False)  # 0.0 to 20.0
    performance_level = db.Column(db.String(50), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="predictions")

    def to_dict(self):
        return {
            "id": self.id,
            "studytime": self.studytime,
            "failures": self.failures,
            "absences": self.absences,
            "predicted_grade": round(self.predicted_grade, 2),
            "performance_level": self.performance_level,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M")
            if self.created_at
            else "",
        }

    def __repr__(self):
        return (
            f"<StudentPrediction User {self.user_id} Grade: {self.predicted_grade}>"
        )
