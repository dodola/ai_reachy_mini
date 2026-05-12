export class ChartManager {
    constructor(canvasElement) {
        this.canvas = canvasElement;
        this.ctx = canvasElement.getContext('2d');
        this.chart = null;
        this.MAX_SAMPLES = 50;

        // Match colors with UIManager
        this.jointColors = {
            'head yaw': '#f472b6',
            'head pitch': '#60a5fa',
            'head roll': '#fbbf24',
            'left antenna': '#34d399',
            'right antenna': '#a78bfa',
            'body yaw': '#fb923c'
        };

        this.init();
    }

    init() {
        const chartData = {
            labels: Array(this.MAX_SAMPLES).fill(''),
            datasets: []
        };

        this.chart = new Chart(this.ctx, {
            type: 'line',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        enabled: false
                    }
                },
                scales: {
                    x: {
                        display: false
                    },
                    y: {
                        ticks: {
                            color: 'rgba(255, 255, 255, 0.4)',
                            font: { size: 10 }
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)'
                        },
                        border: {
                            display: false
                        }
                    }
                },
                elements: {
                    point: { radius: 0 },
                    line: {
                        borderWidth: 1.5,
                        tension: 0.3
                    }
                }
            }
        });
    }

    updateChart(jointValues) {
        // Ensure all datasets exist
        for (const [name, value] of Object.entries(jointValues)) {
            let dataset = this.chart.data.datasets.find(ds => ds.label === name);
            if (!dataset) {
                dataset = {
                    label: name,
                    data: Array(this.MAX_SAMPLES).fill(null),
                    borderColor: this.jointColors[name] || '#ffffff',
                    backgroundColor: 'transparent',
                };
                this.chart.data.datasets.push(dataset);
            }

            // Shift and add new value
            dataset.data.shift();
            dataset.data.push(value);
        }

        this.chart.update('none'); // Update without animation
    }
}
