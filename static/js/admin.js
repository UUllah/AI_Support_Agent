// AI Support Agent - Admin Panel JavaScript

// Show loading indicator
function showAdminLoading() {
    document.getElementById('admin-loading').classList.remove('hidden');
}

// Hide loading indicator
function hideAdminLoading() {
    document.getElementById('admin-loading').classList.add('hidden');
}

// Display admin response
function displayAdminResponse(data, error = false) {
    const output = document.getElementById('admin-response');
    if (error) {
        output.innerHTML = `<span style="color: #e74c3c;">Error: ${JSON.stringify(data, null, 2)}</span>`;
    } else {
        output.textContent = JSON.stringify(data, null, 2);
    }
}

// Load and display schemas
async function loadSchemas() {
    showAdminLoading();

    try {
        const response = await fetch('/api/schemas');
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Failed to load schemas');
        }

        displaySchemas(data.schemas);
        displayAdminResponse({message: `Loaded ${data.schemas.length} schemas successfully`});
    } catch (error) {
        displayAdminResponse({error: error.message}, true);
        displaySchemas([]);
    } finally {
        hideAdminLoading();
    }
}

// Display schemas in the list
function displaySchemas(schemas) {
    const schemaList = document.getElementById('schema-list');

    if (schemas.length === 0) {
        schemaList.innerHTML = '<p>No schemas uploaded yet.</p>';
        return;
    }

    const schemaItems = schemas.map(schema => `
        <div class="schema-item">
            <div>
                <h4>${schema.name}</h4>
                <p>Category: ${schema.category} | Type: ${schema.extension.toUpperCase()}</p>
            </div>
            <div class="schema-actions">
                <button onclick="viewSchema('${schema.category}', '${schema.name}')" class="btn-primary btn-small">View</button>
                <button onclick="deleteSchema('${schema.category}', '${schema.name}')" class="btn-secondary btn-small" style="background: #e74c3c;">Delete</button>
            </div>
        </div>
    `).join('');

    schemaList.innerHTML = schemaItems;
}

// View schema content
async function viewSchema(category, name) {
    showAdminLoading();

    try {
        const response = await fetch(`/api/schemas/${category}/${name}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Failed to load schema content');
        }

        const contentDiv = document.getElementById('schema-content');
        contentDiv.innerHTML = `
            <h4>${data.name} (${data.category})</h4>
            <pre>${data.content}</pre>
        `;

        displayAdminResponse({message: `Loaded schema: ${category}/${name}`});
    } catch (error) {
        displayAdminResponse({error: error.message}, true);
        document.getElementById('schema-content').innerHTML = '<p>Failed to load schema content.</p>';
    } finally {
        hideAdminLoading();
    }
}

// Delete schema
async function deleteSchema(category, name) {
    if (!confirm(`Are you sure you want to delete the schema "${category}/${name}"?`)) {
        return;
    }

    showAdminLoading();

    try {
        const response = await fetch(`/api/schemas/${category}/${name}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Failed to delete schema');
        }

        displayAdminResponse(data);
        // Reload schemas list
        await loadSchemas();
    } catch (error) {
        displayAdminResponse({error: error.message}, true);
    } finally {
        hideAdminLoading();
    }
}

// Handle schema upload
document.getElementById('upload-form').addEventListener('submit', async function(e) {
    e.preventDefault();

    const name = document.getElementById('schema-name').value.trim();
    const category = document.getElementById('schema-category').value;
    const fileInput = document.getElementById('schema-file');

    if (!name || !category || !fileInput.files[0]) {
        displayAdminResponse({error: 'Please fill in all fields and select a file'}, true);
        return;
    }

    const formData = new FormData();
    formData.append('name', name);
    formData.append('category', category);
    formData.append('schema_file', fileInput.files[0]);

    showAdminLoading();

    try {
        const response = await fetch('/api/schemas/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Upload failed');
        }

        displayAdminResponse(data);
        // Clear form
        document.getElementById('upload-form').reset();
        // Reload schemas list
        await loadSchemas();
    } catch (error) {
        displayAdminResponse({error: error.message}, true);
    } finally {
        hideAdminLoading();
    }
});

// Initialize admin panel
document.addEventListener('DOMContentLoaded', function() {
    loadSchemas();
});