"""AI Study Chatbot routes."""

from flask import Blueprint, render_template, request, jsonify
from database.db import db
from models.chat_history import ChatMessage
from routes.auth import login_required, get_current_user
from services.ollama_service import ollama_service

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/chat")
@login_required
def chat_view():
    """Render the AI Study Chatbot interface."""
    user = get_current_user()
    return render_template("chat.html", user=user)


@chat_bp.route("/api/chat", methods=["POST"])
@login_required
def chat_endpoint():
    """Process student academic question using Ollama and maintain conversation history."""
    user = get_current_user()
    data = request.get_json() or {}
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"error": "Message cannot be empty."}), 400

    # 1. Fetch recent conversation history for pedagogical context
    recent_messages = (
        ChatMessage.query.filter_by(user_id=user.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(6)
        .all()
    )
    history_payload = [
        {"role": m.role, "content": m.content} for m in reversed(recent_messages)
    ]

    # 2. Save user message to DB
    user_msg_record = ChatMessage(user_id=user.id, role="user", content=message)
    db.session.add(user_msg_record)

    # 3. Request genuine AI inference from Ollama
    ai_reply = ollama_service.chat_response(message, history=history_payload)

    # 4. Save assistant reply to DB
    assistant_msg_record = ChatMessage(
        user_id=user.id, role="assistant", content=ai_reply
    )
    db.session.add(assistant_msg_record)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to persist chat message: {str(e)}"}), 500

    return jsonify(
        {
            "user_message": user_msg_record.to_dict(),
            "reply": assistant_msg_record.to_dict(),
            "model": ollama_service.model,
            "ollama_active": ollama_service.is_available(),
        }
    )


@chat_bp.route("/api/chat/history", methods=["GET"])
@login_required
def chat_history():
    """Retrieve full chat transcript for the authenticated student."""
    user = get_current_user()
    messages = (
        ChatMessage.query.filter_by(user_id=user.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return jsonify({"messages": [m.to_dict() for m in messages]})


@chat_bp.route("/api/chat/history", methods=["DELETE"])
@login_required
def clear_chat_history():
    """Clear conversation transcript for current student."""
    user = get_current_user()
    try:
        ChatMessage.query.filter_by(user_id=user.id).delete()
        db.session.commit()
        return jsonify({"message": "Conversation history cleared successfully."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to clear history: {str(e)}"}), 500
