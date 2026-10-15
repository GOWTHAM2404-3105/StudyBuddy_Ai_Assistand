# StudyBuddy: College Viva & Faculty Defense Preparation Guide

This guide contains the most critical technical questions, theoretical foundations, and model answers expected during a college project viva or faculty technical review for **StudyBuddy**.

---

## Part 1: Architecture, Web Framework & Security

### Q1: What is the overall architectural design of StudyBuddy?
**Answer:**  
StudyBuddy follows a **modular, decoupled full-stack architecture** organized around the MVC/Services pattern:
1. **Frontend Presentation:** HTML5, CSS3, ES6 JavaScript, Bootstrap 5.3 for responsive styling, and Chart.js 4.4 for dynamic client-side visual telemetry.
2. **REST API & Web Layer:** Python 3.13 and Flask 3.1 using application factories and independent Flask Blueprints (`auth`, `dashboard`, `chat`, `documents`, `quizzes`, `predict`, `recommendations`).
3. **Services & Business Logic Layer:** Modular services decoupled from HTTP routes:
   - `OllamaService` handles local generative AI inference and prompt templating.
   - `RAGService` handles PyMuPDF text parsing, chunking, and vector cosine similarity.
   - `QuizService` handles MCQ schema validation, scoring, and explanations.
   - `RecommendationService` manages topic mastery aggregation and actionable intervention pathways.
   - `predict.py` executes validated Scikit-Learn inference.
4. **Persistence Layer:** SQLite relational database managed via SQLAlchemy 2.0 ORM with isolated filesystem storage for uploaded PDFs.

### Q2: Why did you choose Flask over Django or FastAPI?
**Answer:**  
- **Flask vs. Django:** Django is a heavy, monolithic framework with built-in admin panels and ORMs that add unnecessary overhead for a lightweight AI/ML micro-service application. Flask offers micro-framework simplicity, allowing us to explicitly design our own service boundaries, SQLAlchemy models, and custom AI inference pipelines without framework lock-in.
- **Flask vs. FastAPI:** While FastAPI is excellent for asynchronous APIs, Flask 3.x natively supports both synchronous and asynchronous endpoints, integrates seamlessly with Jinja2 server-rendered templates, and offers rock-solid WSGI deployment maturity across educational environments.

### Q3: How do you enforce student security and data privacy?
**Answer:**  
1. **Password Security:** Student passwords are never stored in plaintext. We utilize **PBKDF2 (Password-Based Key Derivation Function 2) with HMAC-SHA256** via Werkzeug, applying salt and thousands of hashing iterations to thwart rainbow table and brute-force attacks.
2. **Access Control:** A custom `@login_required` decorator validates active server sessions. Unauthorized requests to API endpoints return `HTTP 401 Unauthorized`.
3. **Multi-Tenant Data Isolation:** Every query to uploaded documents, chat transcripts, quizzes, or grade forecasts filters by `user_id = current_user.id`. One student cannot view, modify, or query another student's private notes or exam records.
4. **Zero Cloud Data Leakage:** Because Ollama runs locally on the host machine, no homework questions, student essays, or professor slides are transmitted to third-party commercial cloud APIs.

---

## Part 2: Artificial Intelligence & Semantic RAG

### Q4: What is Retrieval-Augmented Generation (RAG), and why is it necessary?
**Answer:**  
Retrieval-Augmented Generation (RAG) is an AI framework that augments a Large Language Model with external, verified knowledge retrieved dynamically from a corpus of documents before generating a response.  
**Why it is necessary:** Standard LLMs have frozen training data and have no access to a student's specific course syllabus or university lecture slides. Furthermore, standard LLMs suffer from "hallucinations"—fabricating plausible-sounding but completely incorrect facts. RAG grounds the LLM strictly within the retrieved lecture passages, forcing it to cite specific page numbers and answer only with facts present in the student's notes.

### Q5: How does your text extraction and chunking pipeline work?
**Answer:**  
1. **Extraction via PyMuPDF (`pymupdf`):** We ingest the PDF and extract text on a per-page basis, preserving the 1-indexed page number metadata.
2. **Sliding Window Chunking:** Documents are divided into **500-character segments** with a **100-character overlap**.  
   *Why overlap?* Overlap ensures that key concepts or sentences split across a character boundary are not severed, preserving semantic coherence between adjacent chunks.

### Q6: How is semantic similarity calculated? What embedding model is used?
**Answer:**  
- **Embedding Model:** We use **Sentence Transformers (`all-MiniLM-L6-v2`)**, which maps sentences and paragraphs into a dense 384-dimensional vector space.
- **Cosine Similarity:** Given query vector $\vec{q}$ and passage vector $\vec{d}$, cosine similarity measures the cosine of the angle between them:
$$\text{Cosine Similarity}(\vec{q}, \vec{d}) = \frac{\vec{q} \cdot \vec{d}}{\|\vec{q}\| \|\vec{d}\|}$$
Because our embeddings are $L_2$-normalized ($\|\vec{q}\| = \|\vec{d}\| = 1$), cosine similarity simplifies to a computationally fast dot product: $\vec{q} \cdot \vec{d}$.  
- **Fallback Strategy:** If PyTorch is unavailable on resource-constrained hardware, StudyBuddy includes a zero-dependency Scikit-Learn TF-IDF vectorizer fallback that performs statistical cosine similarity over n-grams, guaranteeing zero downtime.

### Q7: How does StudyBuddy prevent the LLM from hallucinating?
**Answer:**  
We employ two strict guardrails in the system prompt:
1. **Mandatory Citations:** The prompt instructs the model to cite the exact source page number for every fact: `[Source Page X]`.
2. **Explicit Refusal Constraint:** If the cosine similarity between the query and the retrieved passages is near zero, or if the retrieved passages do not contain the answer, the model is strictly constrained to output:  
   *"The uploaded notes do not contain enough information to answer this question."*

---

## Part 3: Machine Learning & Performance Prediction

### Q8: What dataset was used, and what are its key features?
**Answer:**  
We utilized the **UCI Student Performance Dataset** (collected by P. Cortez and A. Silva from secondary schools in Portugal):
- Total records: 395 student instances for the Mathematics curriculum (`student-mat.csv`).
- Target variable: $G3$ — Final year academic grade on a 0 to 20 scale.
- Features used in early prediction:
  - `studytime`: Weekly study hours (Tier 1: <2 hrs, Tier 2: 2–5 hrs, Tier 3: 5–10 hrs, Tier 4: >10 hrs).
  - `failures`: Number of past class failures (0 to 4).
  - `absences`: Total days of school absence (0 to 93).

### Q9: Why did you exclude $G1$ and $G2$ in your prediction experiment?
**Answer:**  
In the original UCI dataset, $G1$ is the first period grade and $G2$ is the second period grade. Including $G1$ and $G2$ to predict $G3$ creates **severe data leakage** and trivializes the machine learning task, because a student who scores 18 in $G1$ and $G2$ will almost certainly score 18 in $G3$.  
More importantly, from an educational standpoint, knowing a grade at the end of period 2 is too late for preventive intervention. By strictly excluding $G1$ and $G2$, we formulated a genuine **early-intervention predictive experiment** that forecasts final outcomes at the beginning of the semester based only on attendance, study habits, and past academic history.

### Q10: Why compare Linear Regression against Random Forest? What were the results?
**Answer:**  
- **Linear Regression (Baseline):** Assumes a linear, independent relationship between features and grade.
- **Random Forest Regressor (Ensemble):** Constructs 100 decision trees with bootstrap aggregation (bagging) and feature subsampling. It captures non-linear threshold effects (e.g., how the negative impact of absences accelerates once a student misses more than 10 classes).

**Evaluation Metrics (80/20 Train/Test Split, 5-Fold Cross-Validation):**

| Metric | Linear Regression | Random Forest Regressor | Advantage |
| :--- | :---: | :---: | :---: |
| **5-Fold CV RMSE** | 4.3030 | **4.1317** | Lower error on training cross-validation |
| **Held-Out Test MAE** | 3.5606 | **3.4194** | Random Forest makes smaller average errors |
| **Held-Out Test RMSE** | 4.4581 | **4.2867** | Lower penalty for large outlier mispredictions |
| **Test $R^2$ Score** | 0.0307 | **0.1038** | Explains more variance in early performance |

Random Forest demonstrated superior generalization and was serialized into `data/student_performance_model.joblib`.

### Q11: What are the feature importances extracted from the model?
**Answer:**  
From the fitted Random Forest Regressor:
1. **`absences` (47.39%):** Attendance regularity is the strongest non-linear predictor. High absenteeism has an exponential downward pull on grades.
2. **`failures` (39.98%):** Past class failures indicate underlying conceptual deficiencies that compound into future tests.
3. **`studytime` (12.63%):** Self-directed study hours provide a positive stabilizing effect (e.g. students moving from Tier 1 to Tier 3 see statistically higher grade bands).

### Q12: Why serialize the model with Joblib instead of standard Pickle?
**Answer:**  
Joblib is optimized specifically for Python scientific objects and NumPy arrays. It executes faster disk serialization/deserialization with memory mapping (`mmap`), reducing memory footprint and load times when the Flask application starts up.

---

## Part 4: Active Recall, Quizzes & Recommendations

### Q13: How does the AI Quiz Generator prevent client-side inspect-element cheating?
**Answer:**  
When generating a quiz, questions and four distinct options (`A`, `B`, `C`, `D`) are created alongside the correct answer and explanation. However, in our SQLAlchemy model, the correct option is stored in the database table `quiz_questions.correct_option`.  
When the student loads the exam page, the API route `/api/quizzes/<id>` explicitly strips the `correct_option` and `explanation` fields from the JSON payload. Therefore, even if a tech-savvy student opens browser DevTools, the DOM and network payloads contain zero information about the answer key. Only upon POST submission to `/api/quizzes/submit` does the server evaluate answers and return the score with explanations.

### Q14: How does your recommendation engine work? Why is it rule-based rather than ML?
**Answer:**  
We adhered to strict scientific integrity:  
- **Current Active Engine:** A transparent, deterministic rule-based engine. It calculates average scores across all quiz attempts per subject. If a student's average mastery drops below $70\%$ (or $<60\%$ for critical priority), it prescribes targeted remediation: retry quizzes on that specific topic, deep-dive chat prompts for the AI tutor, and links to matching uploaded lecture PDFs.
- **Why not ML currently?** A machine learning recommendation model (such as Collaborative Filtering or Matrix Factorization) requires thousands of interaction logs across hundreds of concurrent users. Training a model on dummy or arbitrary data would be scientifically deceptive. We engineered a base abstract interface (`BaseRecommendationEngine`), leaving the architecture fully extensible to activate collaborative filtering once real student interaction datasets scale.

### Q15: How were the automated tests implemented?
**Answer:**  
We built 14 unit and integration tests using **Pytest** across 4 test suites:
- `test_auth.py`: Tests user registration, PBKDF2 hashing validity, duplicate checks, login sessions, and unauthorized route rejection.
- `test_ml_predict.py`: Tests Joblib pipeline loading, bounds validation (e.g., negative absences or invalid study time bounds raising `ValueError`), and API prediction formats.
- `test_quiz.py`: Tests 4-option schema integrity, server-side answer hiding, automated scoring calculation, and mistake explanations.
- `test_rag.py`: Tests PyMuPDF page extraction, chunking with metadata, cosine similarity retrieval, and anti-hallucination refusal for irrelevant queries.  
**All 14 tests pass with a 100% success rate.**
