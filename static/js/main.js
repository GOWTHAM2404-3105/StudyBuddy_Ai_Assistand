// Main client-side scripts for StudyBuddy

document.addEventListener("DOMContentLoaded", () => {
    // Sidebar toggle for mobile responsive view
    const sidebarToggle = document.getElementById("sidebarToggle");
    const wrapper = document.getElementById("wrapper");

    if (sidebarToggle && wrapper) {
        sidebarToggle.addEventListener("click", (e) => {
            e.preventDefault();
            wrapper.classList.toggle("toggled");
        });
    }

    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll(".alert-dismissible");
    alerts.forEach((alert) => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 5000);
    });
});
