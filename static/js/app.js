// AI Support Agent - User Interface JavaScript

// Global state for UI toggles
let showSummaryColumn = true;

// Tab switching functionality
function showTab(tabName) {
    // Hide all tabs
    const tabs = document.querySelectorAll('.tab-content');
    tabs.forEach(tab => tab.classList.remove('active'));

    // Remove active class from all buttons
    const buttons = document.querySelectorAll('.tab-btn');
    buttons.forEach(btn => btn.classList.remove('active'));

    // Show selected tab
    document.getElementById(tabName + '-tab').classList.add('active');

    // Add active class to clicked button
    event.target.classList.add('active');
}

// Handle Enter key press in input fields
function handleEnter(event, apiType) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        switch(apiType) {
            case 'search':
                callSearchAPI();
                break;
            case 'sql':
                callSQLAPI();
                break;
            case 'chat':
                callChatAPI();
                break;
        }
    }
}

// Show loading indicator
function showLoading() {
    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('response-output').textContent = '';
}

// Hide loading indicator
function hideLoading() {
    document.getElementById('loading').classList.add('hidden');
}

// Display response
function displayResponse(data, error = false) {
    const output = document.getElementById('response-output');
    if (error) {
        output.innerHTML = `<span style="color: #e74c3c;">Error: ${JSON.stringify(data, null, 2)}</span>`;
    } else {
        // Filter out summary field if toggle is off
        let displayData = data;
        if (!showSummaryColumn && data.results && Array.isArray(data.results)) {
            displayData = {
                ...data,
                results: data.results.map(result => {
                    const {summary, ...rest} = result;
                    return rest;
                })
            };
        }
        output.textContent = JSON.stringify(displayData, null, 2);
    }
}

// API Call functions
async function callSearchAPI() {
    const query = document.getElementById('search-query').value.trim();
    const topK = document.getElementById('search-topk').value;

    if (!query) {
        displayResponse({error: 'Please enter a search query'}, true);
        return;
    }

    // Update toggle state from checkbox
    showSummaryColumn = document.getElementById('toggle-summary').checked;

    showLoading();

    try {
        const response = await fetch('/api/search-tickets', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                top_k: parseInt(topK)
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'API request failed');
        }

        displayResponse(data);
    } catch (error) {
        displayResponse({error: error.message}, true);
    } finally {
        hideLoading();
    }
}

async function callSQLAPI() {
    const query = document.getElementById('sql-query').value.trim();
    const tableName = document.getElementById('sql-table').value.trim();

    if (!query) {
        displayResponse({error: 'Please enter a natural language query'}, true);
        return;
    }

    showLoading();

    try {
        const requestBody = {
            natural_language_query: query
        };

        if (tableName) {
            requestBody.table_name = tableName;
        }

        const response = await fetch('/api/sql-query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'API request failed');
        }

        displayResponse(data);
    } catch (error) {
        displayResponse({error: error.message}, true);
    } finally {
        hideLoading();
    }
}

async function callChatAPI() {
    const query = document.getElementById('chat-query').value.trim();
    const ticketIdsStr = document.getElementById('chat-tickets').value.trim();

    if (!query) {
        displayResponse({error: 'Please enter your question'}, true);
        return;
    }

    if (!ticketIdsStr) {
        displayResponse({error: 'Please enter relevant ticket IDs'}, true);
        return;
    }

    const ticketIds = ticketIdsStr.split(',').map(id => id.trim()).filter(id => id);

    if (ticketIds.length === 0) {
        displayResponse({error: 'Please enter valid ticket IDs'}, true);
        return;
    }

    showLoading();

    try {
        const response = await fetch('/api/summarize-tickets', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                ticket_ids: ticketIds
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'API request failed');
        }

        displayResponse(data);
    } catch (error) {
        displayResponse({error: error.message}, true);
    } finally {
        hideLoading();
    }
}

// Initialize the interface
document.addEventListener('DOMContentLoaded', function() {
    // Set default tab
    showTab('search');

    // Add form submission handlers to prevent default behavior
    document.querySelectorAll('input, textarea').forEach(element => {
        element.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') {
                e.preventDefault();
            }
        });
    });
});