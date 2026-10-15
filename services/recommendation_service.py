import logging
from abc import ABC, abstractmethod
from models.quiz import QuizAttempt, Quiz
from models.document import Document

logger = logging.getLogger(__name__)


class BaseRecommendationEngine(ABC):
    """Abstract interface for student study recommendation engines."""

    @abstractmethod
    def generate_recommendations(self, user_id: int) -> dict:
        pass


class RuleBasedRecommendationEngine(BaseRecommendationEngine):
    """Transparent, deterministic rule-based recommendation engine.

    Analyzes student quiz scores per topic and maps weaknesses (< 70%) to
    targeted revision actions, relevant uploaded notes, and retry quizzes.
    """

    MASTERY_THRESHOLD = 75.0
    NEEDS_REVIEW_THRESHOLD = 60.0

    def generate_recommendations(self, user_id: int) -> dict:
        attempts = (
            QuizAttempt.query.filter_by(user_id=user_id)
            .order_by(QuizAttempt.attempted_at.desc())
            .all()
        )
        user_docs = Document.query.filter_by(user_id=user_id).all()

        if not attempts:
            return {
                "engine_type": "Rule-Based Heuristic (Baseline)",
                "status": "new_student",
                "message": "Welcome! You haven't taken any quizzes yet. Start with a quiz or upload your lecture notes to unlock personalized study recommendations.",
                "topic_analysis": [],
                "recommended_actions": [
                    {
                        "type": "quiz",
                        "title": "Take Your First Diagnostic Quiz",
                        "description": "Generate a quick 5-question quiz on your current subject to establish your learning baseline.",
                        "action_url": "/quizzes",
                    },
                    {
                        "type": "document",
                        "title": "Upload Course Lecture Notes",
                        "description": "Upload a PDF syllabus or lecture slide to generate summaries and ask document-specific questions.",
                        "action_url": "/documents",
                    },
                    {
                        "type": "chat",
                        "title": "Consult StudyBuddy AI Tutor",
                        "description": "Ask StudyBuddy to explain difficult concepts or create a revision schedule for you.",
                        "action_url": "/chat",
                    },
                ],
                "recommended_notes": [],
                "overall_health": "Baseline Setup",
            }

        # Aggregate topic performance
        topic_scores = {}
        for att in attempts:
            topic = att.quiz.topic if att.quiz and att.quiz.topic else "General"
            if topic not in topic_scores:
                topic_scores[topic] = []
            topic_scores[topic].append(att.score)

        topic_analysis = []
        weak_topics = []
        strong_topics = []

        for topic, scores in topic_scores.items():
            avg_score = round(sum(scores) / len(scores), 1)
            attempts_cnt = len(scores)

            if avg_score < self.NEEDS_REVIEW_THRESHOLD:
                status = "Critical Review"
                badge = "danger"
                weak_topics.append((topic, avg_score))
            elif avg_score < self.MASTERY_THRESHOLD:
                status = "Practice Recommended"
                badge = "warning"
                weak_topics.append((topic, avg_score))
            else:
                status = "Mastered"
                badge = "success"
                strong_topics.append((topic, avg_score))

            topic_analysis.append(
                {
                    "topic": topic,
                    "average_score": avg_score,
                    "attempts": attempts_cnt,
                    "status": status,
                    "badge": badge,
                }
            )

        # Sort topics: weakest first
        topic_analysis.sort(key=lambda x: x["average_score"])

        # Build tailored actionable recommendations
        recommended_actions = []
        recommended_notes = []

        for topic, score in weak_topics:
            # 1. Action: Retake or practice quiz on this topic
            recommended_actions.append(
                {
                    "type": "quiz_retry",
                    "title": f"Revise & Retake: {topic}",
                    "description": f"Your current mastery is {score}%. Re-attempt a quiz on this topic to reinforce weak concepts.",
                    "priority": "High" if score < self.NEEDS_REVIEW_THRESHOLD else "Medium",
                    "action_url": "/quizzes",
                }
            )

            # 2. Check if user has uploaded any notes matching this topic
            for doc in user_docs:
                topic_lower = topic.lower()
                doc_text = (doc.filename + " " + (doc.extracted_text or "")).lower()
                if topic_lower in doc_text:
                    if doc not in recommended_notes:
                        recommended_notes.append(doc)

            # 3. Action: Chat with AI Tutor about this topic
            recommended_actions.append(
                {
                    "type": "chat_deep_dive",
                    "title": f"Ask AI Tutor: Core Concepts in {topic}",
                    "description": f"Use the AI study chatbot to get step-by-step explanations and real-world examples for {topic}.",
                    "priority": "Medium",
                    "action_url": f"/chat?topic={topic}",
                }
            )

        # If all topics are mastered
        if not weak_topics and strong_topics:
            recommended_actions.append(
                {
                    "type": "advance",
                    "title": "Outstanding Performance!",
                    "description": f"You have mastered all tested subjects with > {self.MASTERY_THRESHOLD}% average. Ready for advanced topics!",
                    "priority": "Low",
                    "action_url": "/quizzes",
                }
            )

        # Overall health assessment
        overall_avg = round(sum(att.score for att in attempts) / len(attempts), 1)
        if overall_avg >= self.MASTERY_THRESHOLD:
            overall_health = "Strong Mastery"
        elif overall_avg >= self.NEEDS_REVIEW_THRESHOLD:
            overall_health = "Steady Progress (Refinement Needed)"
        else:
            overall_health = "Needs Focused Intervention"

        return {
            "engine_type": "Transparent Rule-Based Heuristic",
            "status": "active",
            "overall_average": overall_avg,
            "overall_health": overall_health,
            "topic_analysis": topic_analysis,
            "recommended_actions": recommended_actions[:6],
            "recommended_notes": [doc.to_dict() for doc in recommended_notes[:4]],
        }


class MLRecommendationEngine(BaseRecommendationEngine):
    """Placeholder architecture for future collaborative/content-based ML recommendation model.

    Note: As per project guidelines, this engine is kept architectural only until a
    formal recommendation dataset (e.g., student-item matrix) is gathered and trained.
    """

    def generate_recommendations(self, user_id: int) -> dict:
        raise NotImplementedError(
            "ML-trained recommendation engine will be activated once student interaction logs reach training threshold."
        )


# Default active recommendation service
recommendation_service = RuleBasedRecommendationEngine()
