"""Machine Learning Academic Performance Prediction routes."""

from flask import Blueprint, render_template, request, jsonify
from database.db import db
from models.prediction import StudentPrediction
from routes.auth import login_required, get_current_user
from ml.predict import validate_and_predict

predict_bp = Blueprint("predict", __name__)


@predict_bp.route("/predict")
@login_required
def predict_view():
    """Render the Machine Learning Performance Prediction page."""
    user = get_current_user()
    predictions = (
        StudentPrediction.query.filter_by(user_id=user.id)
        .order_by(StudentPrediction.created_at.desc())
        .limit(10)
        .all()
    )
    return render_template("predict.html", user=user, predictions=predictions)


@predict_bp.route("/api/predict", methods=["POST"])
@login_required
def predict_endpoint():
    """Run validated ML inference using Random Forest Regressor on UCI Student dataset."""
    user = get_current_user()
    data = request.get_json() or {}

    try:
        studytime = data.get("studytime")
        failures = data.get("failures")
        absences = data.get("absences")

        # Validate and predict
        prediction_result = validate_and_predict(
            studytime=studytime, failures=failures, absences=absences
        )

        # Persist prediction record in DB for student tracking
        record = StudentPrediction(
            user_id=user.id,
            studytime=int(studytime),
            failures=int(failures),
            absences=int(absences),
            predicted_grade=prediction_result["predicted_grade"],
            performance_level=prediction_result["performance_level"],
        )
        db.session.add(record)
        db.session.commit()

        prediction_result["id"] = record.id
        return jsonify(prediction_result)

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Prediction service failed: {str(e)}"}), 500


@predict_bp.route("/api/predict/history", methods=["GET"])
@login_required
def prediction_history():
    """Retrieve student prediction history."""
    user = get_current_user()
    predictions = (
        StudentPrediction.query.filter_by(user_id=user.id)
        .order_by(StudentPrediction.created_at.desc())
        .all()
    )
    return jsonify({"predictions": [p.to_dict() for p in predictions]})
