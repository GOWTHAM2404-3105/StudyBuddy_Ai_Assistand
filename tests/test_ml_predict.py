"""Automated tests for Machine Learning grade prediction pipeline and API."""

import pytest
from app import create_app
from database.db import db
from ml.predict import validate_and_predict, get_trained_model
from models.user import User


@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # Create student user
            u = User(username="testml", email="testml@college.edu")
            u.set_password("Pass123!")
            db.session.add(u)
            db.session.commit()

            # Log in client
            with client.session_transaction() as sess:
                sess["user_id"] = u.id
                sess["username"] = u.username

            yield client
            db.session.remove()
            db.drop_all()


def test_model_artifact_loaded_and_valid():
    """Verify the trained Joblib model artifact contains required metadata and pipeline."""
    artifact = get_trained_model()
    assert artifact is not None
    assert "pipeline" in artifact
    assert "features" in artifact
    assert artifact["features"] == ["studytime", "failures", "absences"]
    assert "metrics" in artifact
    assert "test_mae" in artifact["metrics"]
    assert "test_rmse" in artifact["metrics"]
    assert "feature_importances" in artifact


def test_validate_and_predict_valid_inputs():
    """Test valid inputs produce predictions within 0-20 scale with explanations."""
    result = validate_and_predict(studytime=3, failures=0, absences=2)

    assert "predicted_grade" in result
    assert 0.0 <= result["predicted_grade"] <= 20.0
    assert "performance_level" in result
    assert "recommendation" in result
    assert "disclaimer" in result
    assert "scale" in result
    assert "percentage_equivalent" in result


def test_validate_and_predict_input_bounds():
    """Ensure invalid parameter bounds raise ValueError with clear messages."""
    # studytime out of bounds (< 1 or > 4)
    with pytest.raises(ValueError, match="Study time must be between 1 and 4"):
        validate_and_predict(studytime=5, failures=0, absences=2)

    with pytest.raises(ValueError, match="Study time must be between 1 and 4"):
        validate_and_predict(studytime=0, failures=0, absences=2)

    # failures out of bounds (< 0 or > 4)
    with pytest.raises(ValueError, match="Past class failures"):
        validate_and_predict(studytime=2, failures=-1, absences=2)

    # absences out of bounds
    with pytest.raises(ValueError, match="Absences must be between"):
        validate_and_predict(studytime=2, failures=0, absences=150)


def test_predict_api_endpoint(client):
    """Test POST /api/predict API endpoint."""
    res = client.post(
        "/api/predict",
        json={"studytime": 4, "failures": 0, "absences": 0},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert "predicted_grade" in data
    assert data["studytime"] == 4
    assert data["failures"] == 0
    assert data["absences"] == 0
    assert "id" in data  # Saved to DB
