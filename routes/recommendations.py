"""Personalized Study Recommendations routes."""

from flask import Blueprint, render_template, jsonify
from routes.auth import login_required, get_current_user
from services.recommendation_service import recommendation_service

recommendations_bp = Blueprint("recommendations", __name__)


@recommendations_bp.route("/recommendations")
@login_required
def recommendations_view():
    """Render the Personalized Study Recommendations page."""
    user = get_current_user()
    rec_data = recommendation_service.generate_recommendations(user.id)
    return render_template("recommendations.html", user=user, recommendations=rec_data)


@recommendations_bp.route("/api/recommendations", methods=["GET"])
@login_required
def recommendations_endpoint():
    """API returning student topic mastery, weak areas, and tailored study actions."""
    user = get_current_user()
    rec_data = recommendation_service.generate_recommendations(user.id)
    return jsonify(rec_data)
