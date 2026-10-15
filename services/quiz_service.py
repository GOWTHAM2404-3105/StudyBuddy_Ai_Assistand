import json
import logging
import re
from services.ollama_service import ollama_service

logger = logging.getLogger(__name__)


class QuizService:
    """Service to generate, validate, and evaluate academic multiple-choice quizzes."""

    def generate_quiz_content(
        self, topic: str, context_text: str = None, num_questions: int = 5
    ) -> list:
        """Prompt Ollama to generate MCQs with 4 options and explanations, validating output format."""
        system_prompt = (
            "You are an academic test preparation professor. Create a rigorous, high-quality multiple-choice quiz.\n"
            "Requirements:\n"
            f"1. Generate exactly {num_questions} questions.\n"
            "2. Each question MUST have exactly 4 distinct options: 'A', 'B', 'C', and 'D'.\n"
            "3. Specify the single 'correct_option' ('A', 'B', 'C', or 'D').\n"
            "4. Provide a thorough, educational 'explanation' for why the answer is correct.\n"
            "5. Respond ONLY with valid JSON in this exact structure without markdown commentary:\n"
            "[\n"
            "  {\n"
            '    "question": "Question text here?",\n'
            '    "options": {\n'
            '      "A": "Option 1",\n'
            '      "B": "Option 2",\n'
            '      "C": "Option 3",\n'
            '      "D": "Option 4"\n'
            "    },\n"
            '    "correct_option": "A",\n'
            '    "explanation": "Detailed explanation of why A is correct."\n'
            "  }\n"
            "]"
        )

        user_prompt = f"Topic: {topic}\n"
        if context_text:
            user_prompt += f"Context notes excerpt:\n{context_text[:3500]}\n"
        user_prompt += f"Generate {num_questions} multiple choice questions now."

        raw_response = ollama_service.generate(user_prompt, system=system_prompt)
        parsed_questions = self._parse_and_validate_quiz_json(raw_response)

        if parsed_questions:
            return parsed_questions

        # Fallback question generator if Ollama is not yet downloaded or returned malformed JSON
        logger.info(f"Using fallback structured questions generator for topic '{topic}'")
        return self._generate_fallback_questions(topic, context_text, num_questions)

    def _parse_and_validate_quiz_json(self, raw_text: str) -> list:
        """Sanitize and validate AI JSON response."""
        if not raw_text:
            return []

        cleaned = raw_text.strip()
        # Remove markdown code fences if present
        if "```" in cleaned:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
            if match:
                cleaned = match.group(1).strip()

        try:
            data = json.loads(cleaned)
            if isinstance(data, dict) and "questions" in data:
                data = data["questions"]

            if not isinstance(data, list):
                return []

            valid_questions = []
            for item in data:
                q_text = item.get("question") or item.get("question_text")
                opts = item.get("options", {})
                correct = str(item.get("correct_option") or item.get("correct_answer", "")).upper()
                explanation = item.get("explanation", "Correct based on course syllabus.")

                # Ensure options format
                if isinstance(opts, list) and len(opts) == 4:
                    opts = {"A": str(opts[0]), "B": str(opts[1]), "C": str(opts[2]), "D": str(opts[3])}

                if (
                    q_text
                    and isinstance(opts, dict)
                    and all(k in opts for k in ["A", "B", "C", "D"])
                    and correct in ["A", "B", "C", "D"]
                ):
                    valid_questions.append(
                        {
                            "question": str(q_text).strip(),
                            "options": {k: str(v).strip() for k, v in opts.items()},
                            "correct_option": correct,
                            "explanation": str(explanation).strip(),
                        }
                    )

            return valid_questions
        except Exception as e:
            logger.warning(f"Failed to parse AI quiz JSON: {e}")
            return []

    def _generate_fallback_questions(
        self, topic: str, context_text: str = None, num_questions: int = 5
    ) -> list:
        """Reliable academic questions generator for topics and notes."""
        clean_topic = topic.strip().title()
        templates = [
            {
                "question": f"Which of the following best defines the core principle of {clean_topic}?",
                "options": {
                    "A": f"A foundational methodology designed to systematically analyze and implement {clean_topic}.",
                    "B": "A random trial-and-error heuristic with no theoretical backing.",
                    "C": "A hardware-only component that cannot operate on software algorithms.",
                    "D": "A legacy standard that has been completely deprecated in modern computing.",
                },
                "correct_option": "A",
                "explanation": f"{clean_topic} is established on structured scientific and practical methodologies.",
            },
            {
                "question": f"What is a primary advantage of applying {clean_topic} in real-world systems?",
                "options": {
                    "A": "Guaranteed 100% memory overhead reduction regardless of architecture.",
                    "B": "Enhanced scalability, modular design, and robust problem-solving capability.",
                    "C": "Elimination of all testing and validation procedures.",
                    "D": "Complete avoidance of mathematical modeling.",
                },
                "correct_option": "B",
                "explanation": f"Scalability, structured abstractions, and modularity are standard merits of {clean_topic}.",
            },
            {
                "question": f"Which metric or evaluation technique is most standard when assessing {clean_topic}?",
                "options": {
                    "A": "Line count of code only.",
                    "B": "Validation accuracy, error minimization, and benchmark efficiency.",
                    "C": "Alphabetical ordering of variables.",
                    "D": "Size of physical cooling fans.",
                },
                "correct_option": "B",
                "explanation": "Evaluating solutions requires rigorous performance benchmarks, accuracy metrics, and error tracking.",
            },
            {
                "question": f"In {clean_topic}, what step is critical during the initial development or problem definition phase?",
                "options": {
                    "A": "Skipping requirement analysis to write code immediately.",
                    "B": "Clear requirement formulation, data understanding, and architecture planning.",
                    "C": "Immediate cloud deployment with zero local testing.",
                    "D": "Discarding all domain assumptions.",
                },
                "correct_option": "B",
                "explanation": "Thorough requirement formulation and baseline modeling prevent architectural pitfalls.",
            },
            {
                "question": f"How should edge cases and exceptions be handled within a {clean_topic} implementation?",
                "options": {
                    "A": "Silent failures with ignored exceptions.",
                    "B": "Rigorous boundary validation, defensive logic, and systematic testing.",
                    "C": "Terminating the server on any input variation.",
                    "D": "Hardcoding results for specific edge instances only.",
                },
                "correct_option": "B",
                "explanation": "Defensive programming and boundary validation ensure stability under unforeseen conditions.",
            },
        ]
        return templates[:num_questions]

    def evaluate_submission(self, questions: list, submitted_answers: dict) -> dict:
        """Evaluate student answers, calculate percentage score, and format review details."""
        total = len(questions)
        correct_count = 0
        details = []

        for q in questions:
            qid = str(q.id)
            user_ans = submitted_answers.get(qid, "").strip().upper()
            is_correct = user_ans == q.correct_option

            if is_correct:
                correct_count += 1

            details.append(
                {
                    "question_id": q.id,
                    "question_text": q.question_text,
                    "options": {
                        "A": q.option_a,
                        "B": q.option_b,
                        "C": q.option_c,
                        "D": q.option_d,
                    },
                    "selected_option": user_ans or "Not Answered",
                    "correct_option": q.correct_option,
                    "is_correct": is_correct,
                    "explanation": q.explanation or "Standard academic rationale.",
                }
            )

        score_pct = (correct_count / total * 100.0) if total > 0 else 0.0

        return {
            "total_questions": total,
            "correct_answers": correct_count,
            "score_percentage": round(score_pct, 1),
            "details": details,
        }


quiz_service = QuizService()
