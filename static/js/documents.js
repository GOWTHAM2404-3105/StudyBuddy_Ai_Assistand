// PDF Notes Assistant & Semantic RAG frontend interactions

document.addEventListener("DOMContentLoaded", () => {
    const uploadForm = document.getElementById("uploadDocForm");
    const fileInput = document.getElementById("pdfFileInput");
    const uploadBtn = document.getElementById("uploadDocBtn");
    const uploadStatus = document.getElementById("uploadStatus");

    const ragDocSelect = document.getElementById("ragDocSelect");
    const ragQuestionInput = document.getElementById("ragQuestionInput");
    const ragAskBtn = document.getElementById("ragAskBtn");
    const ragAnswerCard = document.getElementById("ragAnswerCard");
    const ragAnswerText = document.getElementById("ragAnswerText");
    const ragSourcesList = document.getElementById("ragSourcesList");

    // Upload PDF
    if (uploadForm) {
        uploadForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            if (!fileInput.files.length) {
                alert("Please select a PDF file to upload.");
                return;
            }

            const file = fileInput.files[0];
            if (file.type !== "application/pdf" && !file.name.endsWith(".pdf")) {
                alert("Only PDF files are supported.");
                return;
            }

            const formData = new FormData();
            formData.append("file", file);

            uploadBtn.disabled = true;
            uploadStatus.innerHTML = `
                <div class="d-flex align-items-center text-primary small">
                    <span class="spinner-border spinner-border-sm me-2" role="status"></span>
                    <span>Extracting text with PyMuPDF, generating embeddings &amp; summarizing... This may take a few seconds.</span>
                </div>
            `;

            try {
                const res = await fetch("/api/documents", {
                    method: "POST",
                    body: formData,
                });
                const data = await res.json();

                if (res.ok) {
                    uploadStatus.innerHTML = `
                        <div class="alert alert-success py-2 px-3 small mb-0">
                            <i class="bi bi-check-circle-fill me-1"></i> ${data.message}
                        </div>
                    `;
                    setTimeout(() => window.location.reload(), 1500);
                } else {
                    uploadStatus.innerHTML = `
                        <div class="alert alert-danger py-2 px-3 small mb-0">
                            <i class="bi bi-exclamation-triangle-fill me-1"></i> ${data.error || "Upload failed."}
                        </div>
                    `;
                    uploadBtn.disabled = false;
                }
            } catch (err) {
                uploadStatus.innerHTML = `
                    <div class="alert alert-danger py-2 px-3 small mb-0">
                        <i class="bi bi-wifi-off me-1"></i> Network error during upload.
                    </div>
                `;
                uploadBtn.disabled = false;
            }
        });
    }

    // Ask Document Question via RAG
    if (ragAskBtn) {
        ragAskBtn.addEventListener("click", async () => {
            const docId = ragDocSelect ? ragDocSelect.value : null;
            const question = ragQuestionInput ? ragQuestionInput.value.trim() : "";

            if (!docId) {
                alert("Please select an uploaded document first.");
                return;
            }
            if (!question) {
                alert("Please enter a question about your notes.");
                return;
            }

            ragAskBtn.disabled = true;
            ragAskBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Retrieving passages &amp; generating answer...`;
            ragAnswerCard.classList.remove("d-none");
            ragAnswerText.innerHTML = `
                <div class="text-muted fst-italic">
                    <span class="spinner-grow spinner-grow-sm me-1 text-primary"></span>
                    Searching semantic vector space and synthesizing answer from your lecture notes...
                </div>
            `;
            ragSourcesList.innerHTML = "";

            try {
                const res = await fetch("/api/documents/ask", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ document_id: docId, question: question }),
                });
                const data = await res.json();

                if (res.ok) {
                    ragAnswerText.innerHTML = data.answer.replace(/\n/g, "<br>");

                    if (data.sources && data.sources.length > 0) {
                        const pages = data.sources.map(s => `<span class="badge bg-primary-subtle text-primary border border-primary-subtle me-1">Page ${s.page}</span>`).join(" ");
                        ragSourcesList.innerHTML = `<div class="mt-2 small text-muted"><i class="bi bi-bookmarks me-1"></i> Citations: ${pages}</div>`;
                    } else {
                        ragSourcesList.innerHTML = `<div class="mt-2 small text-muted fst-italic"><i class="bi bi-info-circle me-1"></i> No matching passages found in the uploaded text.</div>`;
                    }
                } else {
                    ragAnswerText.innerHTML = `<div class="text-danger"><i class="bi bi-exclamation-circle me-1"></i> ${data.error || "Failed to process question."}</div>`;
                }
            } catch (err) {
                ragAnswerText.innerHTML = `<div class="text-danger"><i class="bi bi-wifi-off me-1"></i> Could not reach server.</div>`;
            } finally {
                ragAskBtn.disabled = false;
                ragAskBtn.innerHTML = `<i class="bi bi-search me-1"></i> Ask Document`;
            }
        });
    }

    // Delete document handler
    document.querySelectorAll(".delete-doc-btn").forEach((btn) => {
        btn.addEventListener("click", async function () {
            const docId = this.getAttribute("data-doc-id");
            const docName = this.getAttribute("data-doc-name");

            if (!confirm(`Are you sure you want to delete '${docName}'? This action cannot be undone.`)) {
                return;
            }

            try {
                const res = await fetch(`/api/documents/${docId}`, { method: "DELETE" });
                const data = await res.json();
                if (res.ok) {
                    const row = document.getElementById(`doc-row-${docId}`);
                    if (row) row.remove();
                    window.location.reload();
                } else {
                    alert(data.error || "Failed to delete document.");
                }
            } catch (err) {
                alert("Network error deleting document.");
            }
        });
    });
});
