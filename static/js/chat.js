// AI Study Chatbot front-end interactions

document.addEventListener("DOMContentLoaded", () => {
    const chatForm = document.getElementById("chatForm");
    const chatInput = document.getElementById("chatInput");
    const chatMessages = document.getElementById("chatMessages");
    const clearChatBtn = document.getElementById("clearChatBtn");
    const sendBtn = document.getElementById("sendBtn");

    if (!chatForm || !chatInput || !chatMessages) return;

    // Scroll to bottom
    const scrollToBottom = () => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    };
    scrollToBottom();

    // Check if URL has ?topic= query param (e.g. from recommendation click)
    const urlParams = new URLSearchParams(window.location.search);
    const prefillTopic = urlParams.get("topic");
    if (prefillTopic) {
        chatInput.value = `Can you explain the core concepts and real-world examples of ${prefillTopic}?`;
        chatInput.focus();
    }

    // Append chat bubble
    const appendMessage = (role, content, time = null) => {
        const bubble = document.createElement("div");
        bubble.className = `chat-bubble ${role}`;
        
        const now = time || new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        
        // Convert simple line breaks to HTML
        const formattedContent = content
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\n/g, "<br>");

        bubble.innerHTML = `
            <div class="chat-text">${formattedContent}</div>
            <span class="chat-timestamp">${now}</span>
        `;
        chatMessages.appendChild(bubble);
        scrollToBottom();
        return bubble;
    };

    // Show typing indicator
    const showTypingIndicator = () => {
        const indicator = document.createElement("div");
        indicator.id = "typingIndicator";
        indicator.className = "chat-bubble assistant";
        indicator.innerHTML = `
            <div class="typing-indicator py-1">
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="small text-muted ms-2">StudyBuddy is thinking...</span>
            </div>
        `;
        chatMessages.appendChild(indicator);
        scrollToBottom();
    };

    const removeTypingIndicator = () => {
        const indicator = document.getElementById("typingIndicator");
        if (indicator) indicator.remove();
    };

    // Handle send message
    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const text = chatInput.value.trim();
        if (!text) return;

        // Display student message
        appendMessage("user", text);
        chatInput.value = "";
        chatInput.disabled = true;
        sendBtn.disabled = true;

        showTypingIndicator();

        try {
            const res = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text })
            });

            const data = await res.json();
            removeTypingIndicator();

            if (res.ok && data.reply) {
                appendMessage("assistant", data.reply.content, data.reply.created_at);
            } else {
                appendMessage("assistant", `⚠️ Error: ${data.error || "Failed to receive response from AI."}`);
            }
        } catch (err) {
            removeTypingIndicator();
            appendMessage("assistant", "⚠️ Network error: Could not reach the server. Please verify your connection.");
        } finally {
            chatInput.disabled = false;
            sendBtn.disabled = false;
            chatInput.focus();
        }
    });

    // Clear chat history
    if (clearChatBtn) {
        clearChatBtn.addEventListener("click", async () => {
            if (!confirm("Are you sure you want to clear your conversation history?")) return;
            try {
                const res = await fetch("/api/chat/history", { method: "DELETE" });
                if (res.ok) {
                    chatMessages.innerHTML = `
                        <div class="text-center text-muted my-4">
                            <i class="bi bi-chat-heart text-primary fs-2"></i>
                            <p class="mt-2 mb-0">Conversation cleared. What topic would you like to study today?</p>
                        </div>
                    `;
                }
            } catch (err) {
                alert("Failed to clear chat history.");
            }
        });
    }
});
