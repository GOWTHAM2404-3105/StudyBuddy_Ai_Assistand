"""PDF Notes Assistant and Semantic RAG routes."""

import os
import uuid
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, jsonify, current_app
from database.db import db
from models.document import Document
from routes.auth import login_required, get_current_user
from services.rag_service import rag_service
from services.ollama_service import ollama_service

documents_bp = Blueprint("documents", __name__)


def allowed_file(filename: str) -> bool:
    """Validate allowed file extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in current_app.config.get(
        "ALLOWED_EXTENSIONS", {"pdf"}
    )


@documents_bp.route("/documents")
@login_required
def documents_view():
    """Render PDF Notes Assistant page."""
    user = get_current_user()
    docs = Document.query.filter_by(user_id=user.id).order_by(Document.created_at.desc()).all()
    return render_template("documents.html", user=user, documents=docs)


@documents_bp.route("/api/documents", methods=["GET"])
@login_required
def list_documents():
    """List documents belonging to the authenticated student."""
    user = get_current_user()
    docs = Document.query.filter_by(user_id=user.id).order_by(Document.created_at.desc()).all()
    return jsonify({"documents": [d.to_dict() for d in docs]})


@documents_bp.route("/api/documents", methods=["POST"])
@login_required
def upload_document():
    """Upload PDF, extract text with PyMuPDF, chunk, summarize, and store."""
    user = get_current_user()

    if "file" not in request.files:
        return jsonify({"error": "No file part in upload request."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF files are supported."}), 400

    # Ensure upload directory exists
    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)

    original_filename = secure_filename(file.filename) or "notes.pdf"
    unique_suffix = uuid.uuid4().hex[:10]
    stored_filename = f"{user.id}_{unique_suffix}_{original_filename}"
    file_path = upload_dir / stored_filename

    # Save to disk
    file.save(str(file_path))
    file_size = os.path.getsize(str(file_path))

    # Extract text and chunk using PyMuPDF and RAG service
    try:
        extracted = rag_service.extract_text_from_pdf(str(file_path))
        page_count = extracted["page_count"]
        pages_data = extracted["pages"]
        full_text = extracted["full_text"]

        if not full_text.strip():
            # Clean up file
            if file_path.exists():
                file_path.unlink()
            return jsonify(
                {
                    "error": "The uploaded PDF appears to be empty or contains only non-extractable images/scans."
                }
            ), 400

        chunks = rag_service.chunk_document(pages_data)

        # Generate summary and key points
        summary_result = ollama_service.summarize_document(full_text[:4000])

        doc = Document(
            user_id=user.id,
            filename=original_filename,
            stored_filename=stored_filename,
            file_path=str(file_path),
            file_size=file_size,
            page_count=page_count,
            extracted_text=full_text,
            summary=summary_result.get("summary", ""),
        )
        doc.set_chunks(chunks)
        doc.set_key_points(summary_result.get("key_points", []))

        db.session.add(doc)
        db.session.commit()

        return jsonify(
            {
                "message": f"Successfully uploaded and processed '{original_filename}' ({page_count} pages).",
                "document": doc.to_dict(),
            }
        ), 201

    except Exception as e:
        db.session.rollback()
        if file_path.exists():
            file_path.unlink()
        return jsonify({"error": f"Failed to process PDF: {str(e)}"}), 500


@documents_bp.route("/api/documents/<int:doc_id>", methods=["GET"])
@login_required
def get_document(doc_id: int):
    """Get single document metadata and summary (enforcing ownership)."""
    user = get_current_user()
    doc = Document.query.filter_by(id=doc_id, user_id=user.id).first()
    if not doc:
        return jsonify({"error": "Document not found or access denied."}), 404
    return jsonify({"document": doc.to_dict()})


@documents_bp.route("/api/documents/<int:doc_id>", methods=["DELETE"])
@login_required
def delete_document(doc_id: int):
    """Delete uploaded document from database and filesystem (enforcing ownership)."""
    user = get_current_user()
    doc = Document.query.filter_by(id=doc_id, user_id=user.id).first()
    if not doc:
        return jsonify({"error": "Document not found or access denied."}), 404

    # Remove file from disk
    try:
        p = Path(doc.file_path)
        if p.exists():
            p.unlink()
    except Exception:
        pass

    db.session.delete(doc)
    db.session.commit()
    return jsonify({"message": f"Document '{doc.filename}' deleted successfully."})


@documents_bp.route("/api/documents/ask", methods=["POST"])
@login_required
def ask_document():
    """RAG endpoint: answers student questions based on selected uploaded PDF."""
    user = get_current_user()
    data = request.get_json() or {}
    doc_id = data.get("document_id")
    question = data.get("question", "").strip()

    if not doc_id:
        return jsonify({"error": "Please specify a document_id."}), 400
    if not question:
        return jsonify({"error": "Question cannot be empty."}), 400

    doc = Document.query.filter_by(id=doc_id, user_id=user.id).first()
    if not doc:
        return jsonify({"error": "Document not found or access denied."}), 404

    chunks = doc.get_chunks()
    if not chunks:
        return jsonify(
            {
                "answer": "The uploaded notes do not contain enough information to answer this question.",
                "sources": [],
            }
        )

    # Perform semantic retrieval and AI question answering
    try:
        rag_output = rag_service.answer_question(question, chunks, top_k=4)
        return jsonify(
            {
                "document_id": doc.id,
                "document_name": doc.filename,
                "question": question,
                "answer": rag_output.get("answer"),
                "sources": rag_output.get("sources", []),
            }
        )
    except Exception as e:
        return jsonify({"error": f"RAG processing failed: {str(e)}"}), 500
