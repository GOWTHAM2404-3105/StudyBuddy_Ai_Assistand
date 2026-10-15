// AI Quiz Generator and Quiz Taking frontend interactions

document.addEventListener("DOMContentLoaded", () => {
    // 1. Quiz Generation Form
    const genQuizForm = document.getElementById("generateQuizForm");
    const genQuizBtn = document.getElementById("generateQuizBtn");
    const genQuizStatus = document.getElementById("generateQuizStatus");

    if (genQuizForm) {
        genQuizForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const topic = document.getElementById("quizTopicInput").value.trim();
            const docId = document.getElementById("quizDocSelect").value;
            const count = document.getElementById("quizCountSelect").value;

            if (!topic && !docId) {
                alert("Please provide a topic name or select an uploaded document.");
                return;
            }

            genQuizBtn.disabled = true;
            genQuizStatus.innerHTML = `
                <div class="d-flex align-items-center text-primary small py-2">
                    <span class="spinner-border spinner-border-sm me-2"></span>
                    <span>Synthesizing multiple-choice questions with 4 options and detailed explanations using AI...</span>
                </div>
            `;

            try {
                const res = await fetch("/api/quizzes/generate", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        topic: topic,
                        document_id: docId || null,
                        num_questions: count,
                    }),
                });

                const data = await res.json();
                if (res.ok && data.quiz) {
                    genQuizStatus.innerHTML = `
                        <div class="alert alert-success py-2 px-3 small">
                            <i class="bi bi-check-circle-fill me-1"></i> ${data.message} Redirecting to quiz...
                        </div>
                    `;
                    setTimeout(() => {
                        window.location.href = `/quizzes/take/${data.quiz.id}`;
                    }, 1200);
                } else {
                    genQuizStatus.innerHTML = `
                        <div class="alert alert-danger py-2 px-3 small">
                            <i class="bi bi-exclamation-triangle-fill me-1"></i> ${data.error || "Failed to generate quiz."}
                        </div>
                    `;
                    genQuizBtn.disabled = false;
                }
            } catch (err) {
                genQuizStatus.innerHTML = `
                    <div class="alert alert-danger py-2 px-3 small">
                        <i class="bi bi-wifi-off me-1"></i> Network error generating quiz.
                    </div>
                `;
                genQuizBtn.disabled = false;
            }
        });
    }

    // 2. Quiz Submission Form
    const submitQuizForm = document.getElementById("takeQuizForm");
    const submitQuizBtn = document.getElementById("submitQuizBtn");

    if (submitQuizForm) {
        submitQuizForm.addEventListener("submit", async (e) => {
            e.preventDefault();

            const quizId = document.getElementById("quizIdInput").value;
            const questionCards = document.querySelectorAll(".quiz-question-card");
            const answers = {};
            let unanswered = 0;

            questionCards.forEach((card) => {
                const qid = card.getAttribute("data-question-id");
                const checked = card.querySelector(`input[name="q_${qid}"]:checked`);
                if (checked) {
                    answers[qid] = checked.value;
                } else {
                    unanswered++;
                }
            });

            if (unanswered > 0) {
                if (!confirm(`You have ${unanswered} unanswered question(s). Do you still wish to submit?`)) {
                    return;
                }
            }

            submitQuizBtn.disabled = true;
            submitQuizBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Evaluating answers...`;

            try {
                const res = await fetch("/api/quizzes/submit", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        quiz_id: quizId,
                        answers: answers,
                    }),
                });

                const data = await res.json();
                if (res.ok && data.attempt_id) {
                    window.location.href = `/quizzes/result/${data.attempt_id}`;
                } else {
                    alert(data.error || "Failed to evaluate quiz submission.");
                    submitQuizBtn.disabled = false;
                    submitQuizBtn.innerHTML = `Submit Quiz`;
                }
            } catch (err) {
                alert("Network error submitting quiz.");
                submitQuizBtn.disabled = false;
                submitQuizBtn.innerHTML = `Submit Quiz`;
            }
        });
    }
});
