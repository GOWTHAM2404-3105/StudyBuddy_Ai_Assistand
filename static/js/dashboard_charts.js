// Interactive Chart.js analytics for Student Dashboard

document.addEventListener("DOMContentLoaded", async () => {
    const topicsChartCanvas = document.getElementById("topicsChart");
    const timelineChartCanvas = document.getElementById("timelineChart");

    if (!topicsChartCanvas || !timelineChartCanvas) return;

    try {
        const res = await fetch("/api/dashboard");
        if (!res.ok) return;

        const data = await res.json();
        const chartsData = data.charts;

        // 1. Topic Mastery Bar Chart
        if (chartsData.topics.labels.length > 0) {
            new Chart(topicsChartCanvas, {
                type: "bar",
                data: {
                    labels: chartsData.topics.labels,
                    datasets: [
                        {
                            label: "Average Score (%)",
                            data: chartsData.topics.scores,
                            backgroundColor: "rgba(13, 110, 253, 0.75)",
                            borderColor: "rgb(13, 110, 253)",
                            borderWidth: 1,
                            borderRadius: 6,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            ticks: {
                                callback: (value) => `${value}%`,
                            },
                        },
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: (ctx) => `Score: ${ctx.raw}%`,
                            },
                        },
                    },
                },
            });
        } else {
            // Render friendly empty state in chart container
            const container = topicsChartCanvas.parentElement;
            container.innerHTML = `
                <div class="text-center py-5 text-muted">
                    <i class="bi bi-bar-chart text-secondary fs-1"></i>
                    <p class="mt-2 mb-0 small">No quiz topic data yet. Take a quiz in Quiz Hub to see your topic mastery chart.</p>
                </div>
            `;
        }

        // 2. Learning Progress Line Chart
        if (chartsData.timeline.labels.length > 0) {
            new Chart(timelineChartCanvas, {
                type: "line",
                data: {
                    labels: chartsData.timeline.labels,
                    datasets: [
                        {
                            label: "Quiz Score (%)",
                            data: chartsData.timeline.scores,
                            fill: true,
                            backgroundColor: "rgba(13, 110, 253, 0.1)",
                            borderColor: "rgb(13, 110, 253)",
                            tension: 0.3,
                            pointBackgroundColor: "rgb(13, 110, 253)",
                            pointRadius: 4,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            ticks: {
                                callback: (value) => `${value}%`,
                            },
                        },
                    },
                    plugins: {
                        legend: { display: false },
                    },
                },
            });
        } else {
            const container = timelineChartCanvas.parentElement;
            container.innerHTML = `
                <div class="text-center py-5 text-muted">
                    <i class="bi bi-graph-up text-secondary fs-1"></i>
                    <p class="mt-2 mb-0 small">No score timeline available yet. As you take quizzes, your progress over time will appear here.</p>
                </div>
            `;
        }
    } catch (err) {
        console.error("Error loading dashboard charts:", err);
    }
});
