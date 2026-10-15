"""StudyBuddy - Student AI Assistant.

Main Flask application entry point.
Pairs genuine NLP, RAG, Ollama AI, and Scikit-learn Machine Learning.
"""

import os
import logging
from flask import Flask, render_template, jsonify
from config import config_by_name
from database.db import db, init_db
from routes import (
    auth_bp,
    dashboard_bp,
    chat_bp,
    documents_bp,
    quizzes_bp,
    predict_bp,
    recommendations_bp,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("StudyBuddy")


def create_app(config_name="development"):
    """Application factory for StudyBuddy."""
    app = Flask(__name__)
    config_obj = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(config_obj)

    # Ensure uploads directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["DATA_DIR"], exist_ok=True)

    # Initialize Database
    init_db(app)

    # Register Blueprint routes
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(quizzes_bp)
    app.register_blueprint(predict_bp)
    app.register_blueprint(recommendations_bp)

    # Register Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        if app.request_class.is_json:
            return jsonify({"error": "Resource not found"}), 404
        return render_template("base.html", error_title="404 - Not Found", error_message="The requested page could not be located."), 404

    @app.errorhandler(413)
    def request_entity_too_large(e):
        return jsonify({"error": "File size exceeds the 16MB limit. Please upload a smaller PDF."}), 413

    @app.errorhandler(500)
    def internal_server_error(e):
        logger.error(f"Internal server error: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

    # Ensure ML model is loaded or trained once at startup
    with app.app_context():
        try:
            from ml.predict import get_trained_model
            get_trained_model()
            logger.info("Machine learning performance prediction model initialized.")
        except Exception as e:
            logger.warning(f"Could not initialize ML model immediately: {e}")

    logger.info("StudyBuddy Flask application initialized successfully.")
    return app


app = create_app(os.getenv("FLASK_ENV", "development"))

if __name__ == "__main__":
    # Host on 127.0.0.1:5000 for local development
    port = int(os.getenv("PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=True)
