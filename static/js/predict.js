// Machine Learning Academic Grade Predictor frontend interactions

document.addEventListener("DOMContentLoaded", () => {
    const predictForm = document.getElementById("predictForm");
    const predictBtn = document.getElementById("predictBtn");
    const predictResultCard = document.getElementById("predictResultCard");
    const predictedGradeDisplay = document.getElementById("predictedGradeDisplay");
    const gradeMeterFill = document.getElementById("gradeMeterFill");
    const performanceBadge = document.getElementById("performanceBadge");
    const recommendationText = document.getElementById("recommendationText");
    const insightsList = document.getElementById("insightsList");
    const modelUsedText = document.getElementById("modelUsedText");

    if (!predictForm) return;

    predictForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const studytime = document.getElementById("studytimeInput").value;
        const failures = document.getElementById("failuresInput").value;
        const absences = document.getElementById("absencesInput").value;

        predictBtn.disabled = true;
        predictBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Running ML Inference...`;

        try {
            const res = await fetch("/api/predict", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    studytime: parseInt(studytime),
                    failures: parseInt(failures),
                    absences: parseInt(absences),
                }),
            });

            const data = await res.json();
            predictBtn.disabled = false;
            predictBtn.innerHTML = `<i class="bi bi-magic me-1"></i> Predict Academic Performance`;

            if (res.ok) {
                predictResultCard.classList.remove("d-none");
                predictResultCard.scrollIntoView({ behavior: "smooth" });

                // Update Grade text
                predictedGradeDisplay.innerHTML = `${data.predicted_grade} <span class="fs-6 text-muted">/ 20</span>`;
                
                // Update Progress meter width
                const pct = data.percentage_equivalent;
                gradeMeterFill.style.width = `${pct}%`;
                
                // Color bar depending on level
                gradeMeterFill.className = `grade-meter-fill bg-${data.level_class}`;

                // Update badge
                performanceBadge.className = `badge bg-${data.level_class} fs-6 px-3 py-2`;
                performanceBadge.innerText = data.performance_level;

                // Update recommendations
                recommendationText.innerText = data.recommendation;

                // Model metadata
                if (modelUsedText) {
                    modelUsedText.innerText = `Model: ${data.model_used} (Test MAE: ${data.model_metrics.test_mae || 'N/A'}, RMSE: ${data.model_metrics.test_rmse || 'N/A'})`;
                }

                // Update insights
                if (insightsList) {
                    if (data.insights && data.insights.length > 0) {
                        insightsList.innerHTML = data.insights
                            .map((ins) => `<li class="mb-1"><i class="bi bi-info-circle text-primary me-2"></i>${ins}</li>`)
                            .join("");
                    } else {
                        insightsList.innerHTML = `<li><i class="bi bi-check-circle text-success me-2"></i>Strong indicators: Balanced attendance and steady study schedule.</li>`;
                    }
                }
            } else {
                alert(data.error || "Prediction request failed.");
            }
        } catch (err) {
            predictBtn.disabled = false;
            predictBtn.innerHTML = `<i class="bi bi-magic me-1"></i> Predict Academic Performance`;
            alert("Network error connecting to prediction model.");
        }
    });
});
