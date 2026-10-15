from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.chat import chat_bp
from routes.documents import documents_bp
from routes.quizzes import quizzes_bp
from routes.predict import predict_bp
from routes.recommendations import recommendations_bp

__all__ = [
    "auth_bp",
    "dashboard_bp",
    "chat_bp",
    "documents_bp",
    "quizzes_bp",
    "predict_bp",
    "recommendations_bp",
]
