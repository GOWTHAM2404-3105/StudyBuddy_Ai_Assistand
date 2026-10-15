"""Automated tests for Quiz generation, evaluation, scoring, and history."""

import pytest
from app import create_app
from database.db import db
from models.user import User
from models.quiz import Quiz, QuizQuestion, QuizAttempt
from services.quiz_service import quiz_service


@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            u = User(username="quizuser", email="quizuser@college.edu")
            u.set_password("Pass123!")
            db.session.add(u)
            db.session.commit()

            with client.session_transaction() as sess:
                sess["user_id"] = u.id
                sess["username"] = u.username

            yield client
            db.session.remove()
            db.drop_all()


def test_quiz_generator_format_and_structure():
    """Verify that generated quiz questions have 4 distinct options and an explanation."""
    questions = quiz_service.generate_quiz_content("Data Structures", num_questions=3)
    assert len(questions) == 3

    for q in questions:
        assert "question" in q
        assert "options" in q
        assert set(q["options"].keys()) == {"A", "B", "C", "D"}
        assert q["correct_option"] in ["A", "B", "C", "D"]
        assert "explanation" in q
        assert len(q["explanation"]) > 0


def test_quiz_service_evaluation():
    """Test automatic scoring and explanation formatting for student answers."""
    # Create mock questions
    class MockQuestion:
        def __init__(self, qid, correct):
            self.id = qid
            self.question_text = f"Sample question {qid}?"
            self.option_a = "Option 1"
            self.option_b = "Option 2"
            self.option_c = "Option 3"
            self.option_d = "Option 4"
            self.correct_option = correct
            self.explanation = f"Explanation for {qid}"

    mock_questions = [
        MockQuestion(1, "A"),
        MockQuestion(2, "B"),
        MockQuestion(3, "C"),
        MockQuestion(4, "D"),
    ]

    # Student answers: Q1 correct (A), Q2 wrong (A), Q3 correct (C), Q4 unanswered
    student_answers = {"1": "A", "2": "A", "3": "C"}
    eval_res = quiz_service.evaluate_submission(mock_questions, student_answers)

    assert eval_res["total_questions"] == 4
    assert eval_res["correct_answers"] == 2
    assert eval_res["score_percentage"] == 50.0
    assert len(eval_res["details"]) == 4

    # Verify explanations are included
    assert eval_res["details"][0]["is_correct"] is True
    assert eval_res["details"][1]["is_correct"] is False
    assert eval_res["details"][1]["correct_option"] == "B"
    assert eval_res["details"][1]["explanation"] == "Explanation for 2"


def test_quiz_generation_and_taking_api(client):
    """End-to-end test of generating a quiz, taking it, hiding answers, and submitting."""
    # 1. Generate quiz via API
    gen_res = client.post(
        "/api/quizzes/generate",
        json={"topic": "Operating Systems", "num_questions": 3},
    )
    assert gen_res.status_code == 201
    quiz_data = gen_res.get_json()["quiz"]
    quiz_id = quiz_data["id"]

    # 2. Verify questions are present and correct answers are hidden
    fetch_res = client.get(f"/api/quizzes/{quiz_id}")
    assert fetch_res.status_code == 200
    fetched_quiz = fetch_res.get_json()["quiz"]
    assert len(fetched_quiz["questions"]) == 3
    for q in fetched_quiz["questions"]:
        assert "correct_option" not in q  # Hidden from student

    # 3. Submit answers
    q1 = fetched_quiz["questions"][0]["id"]
    sub_res = client.post(
        "/api/quizzes/submit",
        json={"quiz_id": quiz_id, "answers": {str(q1): "A"}},
    )
    assert sub_res.status_code == 200
    sub_data = sub_res.get_json()
    assert "attempt_id" in sub_data
    assert "score" in sub_data
    assert "details" in sub_data
