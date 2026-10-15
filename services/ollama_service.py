import os
import json
import logging
import requests
from flask import current_app

logger = logging.getLogger(__name__)


class OllamaService:
    """Service to interact with local Ollama instance for AI generation."""

    def __init__(self, base_url=None, model=None, timeout=None):
        self._base_url = base_url
        self._model = model
        self._timeout = timeout

    @property
    def base_url(self):
        if self._base_url:
            return self._base_url
        try:
            return current_app.config.get("OLLAMA_BASE_URL", "http://localhost:11434")
        except Exception:
            return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    @property
    def model(self):
        if self._model:
            return self._model
        try:
            return current_app.config.get("OLLAMA_MODEL", "llama3.2")
        except Exception:
            return os.getenv("OLLAMA_MODEL", "llama3.2")

    @property
    def timeout(self):
        if self._timeout:
            return self._timeout
        try:
            return current_app.config.get("OLLAMA_TIMEOUT", 60)
        except Exception:
            return int(os.getenv("OLLAMA_TIMEOUT", "60"))

    def is_available(self) -> bool:
        """Check if local Ollama daemon is active and responding."""
        try:
            res = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return res.status_code == 200
        except Exception:
            return False

    def list_models(self):
        """List locally pulled Ollama models."""
        try:
            res = requests.get(f"{self.base_url}/api/tags", timeout=3)
            if res.status_code == 200:
                data = res.json()
                return [m.get("name") for m in data.get("models", [])]
        except Exception as e:
            logger.warning(f"Could not retrieve Ollama models: {e}")
        return []

    def generate(self, prompt: str, system: str = None) -> str:
        """Generate response from Ollama with error handling and informative fallback."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        try:
            res = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            )
            if res.status_code == 200:
                data = res.json()
                return data.get("response", "").strip()
            elif res.status_code == 404:
                return (
                    f"Model '{self.model}' was not found in your local Ollama installation. "
                    f"Please run 'ollama run {self.model}' in your terminal to download it."
                )
            else:
                return f"Ollama returned HTTP error status {res.status_code}: {res.text}"
        except requests.exceptions.ConnectionError:
            logger.warning("Ollama connection failed - daemon is not running.")
            return (
                "⚠️ Ollama is currently offline or unreachable at "
                f"{self.base_url}.\n\n"
                "To enable genuine local AI responses:\n"
                "1. Download Ollama from https://ollama.com\n"
                f"2. Open a terminal and run: `ollama run {self.model}`\n"
                "3. Refresh or ask your question again."
            )
        except requests.exceptions.Timeout:
            return (
                "⏳ Ollama request timed out. If your model is large, please allow more time "
                "or consider switching to a lighter model like `llama3.2:1b` or `qwen2.5:3b` in config.py."
            )
        except Exception as e:
            logger.error(f"Ollama generation unexpected error: {e}")
            return f"An error occurred while contacting AI model: {str(e)}"

    def chat_response(self, user_message: str, history: list = None) -> str:
        """Academic study chatbot response with pedagogical context."""
        system_prompt = (
            "You are StudyBuddy, an encouraging, patient, and highly knowledgeable "
            "academic AI study tutor for college students. "
            "Your goals:\n"
            "- Explain concepts in simple, accessible language without sacrificing accuracy.\n"
            "- Provide clear step-by-step breakdowns for complex topics or math/code.\n"
            "- Include concrete examples, real-world analogies, and memory aids.\n"
            "- Maintain an engaging, respectful, and motivating tone.\n"
            "- If a student asks how to solve a problem, guide them through the logic."
        )

        formatted_prompt = ""
        if history:
            formatted_prompt += "Previous conversation:\n"
            for msg in history[-6:]:
                role_label = "Student" if msg.get("role") == "user" else "Tutor"
                formatted_prompt += f"{role_label}: {msg.get('content')}\n"
            formatted_prompt += "\n"

        formatted_prompt += f"Student: {user_message}\nTutor:"
        return self.generate(formatted_prompt, system=system_prompt)

    def answer_document_question(self, question: str, context_passages: list) -> str:
        """RAG question answering over retrieved document passages."""
        if not context_passages:
            return "The uploaded notes do not contain enough information to answer this question."

        context_str = "\n\n---\n\n".join(
            [
                f"[Source Page {p.get('page', 'Unknown')}]:\n{p.get('text', '')}"
                for p in context_passages
            ]
        )

        system_prompt = (
            "You are a strict, precise academic assistant answering questions based ONLY on the "
            "provided study notes. "
            "Rules:\n"
            "1. Answer strictly using information found in the Context Passages.\n"
            "2. Whenever citing a fact, mention the source page number (e.g., '[Page X]').\n"
            "3. If the Context Passages DO NOT contain sufficient information to answer the question, "
            "you MUST state: 'The uploaded notes do not contain enough information to answer this question.' "
            "Do NOT make up facts or use external knowledge when the document does not mention it.\n"
            "4. Keep answers concise, factual, and well-structured with bullet points."
        )

        prompt = f"Context Passages from uploaded notes:\n{context_str}\n\nStudent Question: {question}\n\nAnswer:"
        return self.generate(prompt, system=system_prompt)

    def summarize_document(self, text_sample: str) -> dict:
        """Generate chapter summary and bulleted key points."""
        system_prompt = (
            "You are an academic summarization expert. Read the text and produce:\n"
            "1. An executive summary paragraph (3-5 sentences).\n"
            "2. 5 to 7 key takeaway bullet points.\n"
            "Format your answer as valid JSON with keys 'summary' (string) and 'key_points' (list of strings)."
        )

        prompt = f"Study Notes Content:\n{text_sample[:4000]}\n\nJSON Output:"
        raw_response = self.generate(prompt, system=system_prompt)

        try:
            cleaned = raw_response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()
            parsed = json.loads(cleaned)
            if "summary" in parsed and "key_points" in parsed:
                return parsed
        except Exception:
            pass

        lines = [line.strip() for line in raw_response.split("\n") if line.strip()]
        points = [line.lstrip("-*• 0123456789.") for line in lines if line.startswith(("-", "*", "•"))]
        return {
            "summary": raw_response[:400] if raw_response else "Summary generated from uploaded notes.",
            "key_points": points[:7] if points else ["Key concept overview", "Important definitions and rules"],
        }


ollama_service = OllamaService()
