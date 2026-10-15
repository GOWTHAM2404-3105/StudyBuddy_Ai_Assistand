"""Automated tests for student authentication, registration, and session isolation."""

import pytest
from app import create_app
from database.db import db
from models.user import User


@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()


def test_user_registration_and_hashing(client):
    """Test successful student registration and secure password hashing."""
    res = client.post(
        "/register",
        json={
            "username": "alice",
            "email": "alice@college.edu",
            "password": "Password123!",
            "full_name": "Alice Smith",
        },
    )
    assert res.status_code == 201
    data = res.get_json()
    assert data["user"]["username"] == "alice"

    with client.application.app_context():
        user = User.query.filter_by(username="alice").first()
        assert user is not None
        assert user.password_hash != "Password123!"  # Never stored plaintext
        assert user.check_password("Password123!") is True
        assert user.check_password("WrongPassword") is False


def test_duplicate_registration_rejected(client):
    """Ensure duplicate username or email returns 409 Conflict."""
    payload = {
        "username": "bob",
        "email": "bob@college.edu",
        "password": "Password123!",
        "full_name": "Bob Vance",
    }
    res1 = client.post("/register", json=payload)
    assert res1.status_code == 201

    # Clear session/logout to test duplicate registration
    client.get("/logout")

    # Attempt duplicate username
    res2 = client.post("/register", json=payload)
    assert res2.status_code == 409


def test_login_flow_and_session(client):
    """Test valid login, bad password, and protected routes."""
    # Register user
    client.post(
        "/register",
        json={
            "username": "carol",
            "email": "carol@college.edu",
            "password": "SecretPassword456!",
        },
    )

    # Logout to test login
    client.get("/logout")

    # Failed login with wrong password
    bad_login = client.post(
        "/login",
        json={"identifier": "carol", "password": "IncorrectPassword"},
    )
    assert bad_login.status_code == 401

    # Successful login
    good_login = client.post(
        "/login",
        json={"identifier": "carol", "password": "SecretPassword456!"},
    )
    assert good_login.status_code == 200

    # Access protected API route
    dash_res = client.get("/api/dashboard")
    assert dash_res.status_code == 200
    assert dash_res.get_json()["user"]["username"] == "carol"

    # Logout
    logout_res = client.get("/logout")
    assert logout_res.status_code == 302

    # Access protected API route after logout
    logged_out_res = client.get("/api/dashboard")
    assert logged_out_res.status_code == 401
