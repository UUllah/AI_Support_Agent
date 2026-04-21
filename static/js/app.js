// AI Operations Dashboard - User Interface JavaScript

let showSummaryColumn = true;
const charts = {};

function showTab(tabName, clickedButton = null) {
    document.querySelectorAll('.tab-content').forEach((tab) => tab.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach((btn) => btn.classList.remove('active'));
    document.getElementById(`${tabName}-tab`).classList.add('active');
    if (clickedButton) {
        clickedButton.classList.add('active');
    }
}

function handleEnter(event, apiType) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        if (apiType === 'search') callSearchAPI();
        if (apiType === 'sql') callSQLAPI();
        if (apiType === 'chat') callChatAPI();
    }
}

function showLoading() {
    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('response-output').textContent = '';
}

function hideLoading() {
    document.getElementById('loading').classList.add('hidden');
}

function displayResponse(data, error = false) {
    const output = document.getElementById('response-output');
    if (error) {
        output.innerHTML = `<span style="color: #e74c3c;">Error: ${JSON.stringify(data, null, 2)}</span>`;
        return;
    }

    let displayData = data;
    if (!showSummaryColumn && data.results && Array.isArray(data.results)) {
        displayData = {
            ...data,
            results: data.results.map((result) => {
                const { summary, ...rest } = result;
                return rest;
            }),
        };
    }
    output.textContent = JSON.stringify(displayData, null, 2);
}

function createMetricCards(containerId, metrics) {
    const container = document.getElementById(containerId);
    container.innerHTML = metrics.map((metric) => `
        <div class="metric-card">
            <span class="metric-label">${metric.label}</span>
            <strong class="metric-value">${metric.value}</strong>
            ${metric.subtext ? `<span class="metric-subtext">${metric.subtext}</span>` : ''}
        </div>
    `).join('');
}

function updateTable(tableId, rows, emptyColspan, renderer) {
    const tbody = document.querySelector(`#${tableId} tbody`);
    if (!rows.length) {
        tbody.innerHTML = `<tr><td colspan="${emptyColspan}" class="muted-cell">No data available.</td></tr>`;
        return;
    }
    tbody.innerHTML = rows.map(renderer).join('');
}

function buildChart(canvasId, config) {
    if (charts[canvasId]) {
        charts[canvasId].destroy();
    }
    const canvas = document.getElementById(canvasId);
    charts[canvasId] = new Chart(canvas, config);
}

function renderTicketDashboard(summary) {
    const categoryRows = summary.categories.filter((item) => item.count > 0);
    createMetricCards('ticket-metrics', [
        { label: 'Loaded Tickets', value: summary.total_tickets },
        { label: 'Active Categories', value: categoryRows.length },
        { label: 'Top Issue Category', value: summary.top_recurring_category.name },
        { label: 'Top Category Share', value: `${summary.top_recurring_category.percentage}%` },
    ]);

    document.getElementById('top-category-card').className = 'highlight-card';
    document.getElementById('top-category-card').innerHTML = `
        <strong>${summary.top_recurring_category.name}</strong>
        <span>${summary.top_recurring_category.count} tickets</span>
        <span>${summary.top_recurring_category.percentage}% of analyzed load</span>
        <span>Ticket IDs: ${(summary.top_recurring_category.top_ticket_ids || []).join(', ') || 'N/A'}</span>
    `;

    buildChart('ticket-category-chart', {
        type: 'pie',
        data: {
            labels: categoryRows.map((item) => item.name),
            datasets: [{
                data: categoryRows.map((item) => item.count),
                backgroundColor: ['#3498db', '#9b59b6', '#2ecc71', '#f39c12', '#e74c3c', '#1abc9c', '#34495e', '#16a085', '#8e44ad', '#95a5a6'],
            }],
        },
        options: { responsive: true, maintainAspectRatio: false },
    });

    buildChart('ticket-daily-chart', {
        type: 'line',
        data: {
            labels: summary.daily_trend.map((item) => item.period),
            datasets: [{
                label: 'Daily Ticket Volume',
                data: summary.daily_trend.map((item) => item.total),
                borderColor: '#3498db',
                backgroundColor: 'rgba(52, 152, 219, 0.2)',
                fill: true,
                tension: 0.3,
            }],
        },
        options: { responsive: true, maintainAspectRatio: false },
    });

    buildChart('ticket-weekly-chart', {
        type: 'bar',
        data: {
            labels: summary.weekly_trend.map((item) => item.period),
            datasets: [{
                label: 'Weekly Ticket Volume',
                data: summary.weekly_trend.map((item) => item.total),
                backgroundColor: '#9b59b6',
            }],
        },
        options: { responsive: true, maintainAspectRatio: false },
    });

    updateTable('ticket-category-table', categoryRows, 4, (item) => `
        <tr>
            <td>${item.name}</td>
            <td>${item.count}</td>
            <td>${item.percentage}%</td>
            <td>${item.top_ticket_ids.join(', ') || 'N/A'}</td>
        </tr>
    `);

    updateTable('top-ticket-table', summary.top_tickets || [], 4, (item) => `
        <tr>
            <td>${item.ticket_id}</td>
            <td>${item.category}</td>
            <td>${item.subject || 'N/A'}</td>
            <td>${item.insight || 'N/A'}</td>
        </tr>
    `);
}

function renderLogAnalytics(summary) {
    const metrics = summary.metrics;
    createMetricCards('log-metrics', [
        { label: 'Total API Hits', value: metrics.total_api_hits },
        { label: 'TPM', value: metrics.transactions_per_minute },
        { label: 'RPM', value: metrics.requests_per_minute },
        { label: 'Error Rate', value: `${metrics.error_rate_percentage}%` },
        { label: '4xx Count', value: metrics.status_4xx_count },
        { label: '5xx Count', value: metrics.status_5xx_count },
        { label: 'Avg Response Time', value: `${metrics.average_response_time_ms} ms` },
        { label: 'P95 Response Time', value: `${metrics.p95_response_time_ms} ms` },
    ]);

    document.getElementById('raw-log-preview').textContent = (summary.raw_preview || []).join('\n') || 'No raw log preview available.';

    const inferredFields = Object.entries(summary.field_inference || {})
        .map(([field, present]) => `<span class="field-chip ${present ? 'present' : 'missing'}">${field}: ${present ? 'detected' : 'missing'}</span>`)
        .join('');
    document.getElementById('parsed-field-preview').innerHTML = `
        <div class="field-chip-row">${inferredFields || '<span class="muted">No fields detected yet.</span>'}</div>
        <div class="detected-pattern">Detected pattern: <strong>${summary.detected_pattern}</strong></div>
        <div class="detected-pattern">Peak hours: ${(metrics.peak_hours || []).map((item) => `${item.hour}:00 (${item.hits})`).join(', ') || 'N/A'}</div>
        <div class="detected-pattern">Non-peak hours: ${(metrics.non_peak_hours || []).map((item) => `${item.hour}:00 (${item.hits})`).join(', ') || 'N/A'}</div>
    `;

    buildChart('log-hourly-chart', {
        type: 'bar',
        data: {
            labels: summary.hourly_distribution.map((item) => `${item.hour}:00`),
            datasets: [{
                label: 'Requests by Hour',
                data: summary.hourly_distribution.map((item) => item.hits),
                backgroundColor: '#2ecc71',
            }],
        },
        options: { responsive: true, maintainAspectRatio: false },
    });

    updateTable('parsed-log-table', summary.parsed_preview || [], 6, (item) => `
        <tr>
            <td>${item.timestamp || 'N/A'}</td>
            <td>${item.method || 'N/A'}</td>
            <td>${item.endpoint || 'N/A'}</td>
            <td>${item.status || 'N/A'}</td>
            <td>${item.response_time != null ? `${item.response_time} ms` : 'N/A'}</td>
            <td>${item.ip || 'N/A'}</td>
        </tr>
    `);

    updateTable('log-endpoint-table', metrics.top_endpoints || [], 2, (item) => `
        <tr>
            <td>${item.endpoint}</td>
            <td>${item.hits}</td>
        </tr>
    `);

    updateTable('failed-api-table', metrics.top_failed_apis || [], 2, (item) => `
        <tr>
            <td>${item.endpoint}</td>
            <td>${item.failures}</td>
        </tr>
    `);
}

async function analyzeTickets() {
    try {
        const response = await fetch('/analyze-tickets', { method: 'POST' });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Ticket analysis failed');
        }
        renderTicketDashboard(data);
    } catch (error) {
        displayResponse({ error: error.message }, true);
    }
}

async function loadTicketSummary() {
    try {
        const response = await fetch('/ticket-summary');
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Unable to load ticket summary');
        }
        renderTicketDashboard(data);
    } catch (error) {
        console.error(error);
    }
}

async function uploadLogFile() {
    const fileInput = document.getElementById('log-file');
    const file = fileInput.files[0];
    if (!file) {
        displayResponse({ error: 'Select a .log or .txt file first.' }, true);
        return;
    }

    const formData = new FormData();
    formData.append('log_file', file);

    try {
        const response = await fetch('/upload-log', {
            method: 'POST',
            body: formData,
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Log analysis failed');
        }
        renderLogAnalytics(data);
    } catch (error) {
        displayResponse({ error: error.message }, true);
    }
}

async function loadLogSummary() {
    try {
        const response = await fetch('/log-summary');
        const data = await response.json();
        if (response.ok) {
            renderLogAnalytics(data);
        }
    } catch (error) {
        console.error(error);
    }
}

async function callSearchAPI() {
    const query = document.getElementById('search-query').value.trim();
    const topK = document.getElementById('search-topk').value;
    if (!query) {
        displayResponse({ error: 'Please enter a search query' }, true);
        return;
    }

    showSummaryColumn = document.getElementById('toggle-summary').checked;
    showLoading();
    try {
        const response = await fetch('/api/search-tickets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, top_k: parseInt(topK, 10) }),
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'API request failed');
        }
        displayResponse(data);
    } catch (error) {
        displayResponse({ error: error.message }, true);
    } finally {
        hideLoading();
    }
}

async function callSQLAPI() {
    const query = document.getElementById('sql-query').value.trim();
    const tableName = document.getElementById('sql-table').value.trim();
    if (!query) {
        displayResponse({ error: 'Please enter a natural language query' }, true);
        return;
    }

    showLoading();
    try {
        const requestBody = { natural_language_query: query };
        if (tableName) {
            requestBody.table_name = tableName;
        }

        const response = await fetch('/api/sql-query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody),
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'API request failed');
        }
        displayResponse(data);
    } catch (error) {
        displayResponse({ error: error.message }, true);
    } finally {
        hideLoading();
    }
}

async function callChatAPI() {
    const query = document.getElementById('chat-query').value.trim();
    const ticketIdsStr = document.getElementById('chat-tickets').value.trim();
    if (!query) {
        displayResponse({ error: 'Please enter your question' }, true);
        return;
    }
    if (!ticketIdsStr) {
        displayResponse({ error: 'Please enter relevant ticket IDs' }, true);
        return;
    }

    const ticketIds = ticketIdsStr.split(',').map((id) => id.trim()).filter(Boolean);
    if (!ticketIds.length) {
        displayResponse({ error: 'Please enter valid ticket IDs' }, true);
        return;
    }

    showLoading();
    try {
        const response = await fetch('/api/summarize-tickets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, ticket_ids: ticketIds }),
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'API request failed');
        }
        displayResponse(data);
    } catch (error) {
        displayResponse({ error: error.message }, true);
    } finally {
        hideLoading();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const defaultButton = document.querySelector('.tab-btn.active');
    showTab('tickets', defaultButton);
    loadTicketSummary();
    loadLogSummary();

    document.querySelectorAll('input, textarea').forEach((element) => {
        element.addEventListener('keypress', (event) => {
            if (event.key === 'Enter' && event.target.tagName !== 'TEXTAREA') {
                event.preventDefault();
            }
        });
    });
});