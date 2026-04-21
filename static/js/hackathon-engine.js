const state = {
    ideasPayload: null,
    selectedIdeaId: null,
    selectedMode: 'roadmap',
    roadmapPayload: null
};

const STORAGE_KEY = 'ai_hackathon_engine_state_v1';

function setStatus(label, tone) {
    const badge = document.getElementById('engine-status-badge');
    badge.textContent = label;
    badge.className = `status-badge ${tone}`;
}

function appendLog(message) {
    const log = document.getElementById('live-log');
    const item = document.createElement('div');
    item.className = 'log-item';
    item.textContent = message;
    log.prepend(item);
}

function persistState() {
    const problemStatement = document.getElementById('problem-statement')?.value || '';
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
        problemStatement,
        ideasPayload: state.ideasPayload,
        selectedIdeaId: state.selectedIdeaId,
        selectedMode: state.selectedMode,
        roadmapPayload: state.roadmapPayload
    }));
}

function updateExportButtons() {
    const disabled = !state.roadmapPayload;
    document.getElementById('export-json-btn').disabled = disabled;
    document.getElementById('export-md-btn').disabled = disabled;
}

function setRoadmapPlaceholder(message) {
    const container = document.getElementById('roadmap-container');
    container.className = 'roadmap-output empty-state';
    container.textContent = message;
    state.roadmapPayload = null;
    updateExportButtons();
    persistState();
}

function escapeHtml(value) {
    return value
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function renderIdeas(payload) {
    state.ideasPayload = payload;
    persistState();
    const container = document.getElementById('ideas-container');
    const recommendedId = payload.recommended_idea_id;
    document.getElementById('recommendation-pill').classList.remove('hidden');
    container.className = 'ideas-grid';

    container.innerHTML = payload.ideas.map((idea, index) => {
        const recommendedClass = idea.id === recommendedId ? 'recommended-card' : '';
        const activeClass = idea.id === state.selectedIdeaId ? 'selected-card' : '';
        return `
            <article class="idea-card ${recommendedClass} ${activeClass}" data-idea-id="${idea.id}">
                <div class="idea-rank">#${index + 1}</div>
                <div class="idea-card-header">
                    <h3>${escapeHtml(idea.title)}</h3>
                    <span class="score-chip">Score ${idea.weighted_score}</span>
                </div>
                <p class="idea-summary">${escapeHtml(idea.solution_summary || idea.problem_understanding)}</p>
                <div class="idea-metrics">
                    <span>Impact: ${escapeHtml(idea.business_impact)}</span>
                    <span>Ease: ${escapeHtml(idea.ease_of_implementation)}</span>
                    <span>Innovation: ${escapeHtml(idea.innovation_level)}</span>
                    <span>Feasibility: ${escapeHtml(idea.real_world_feasibility)}</span>
                </div>
                <div class="idea-fit-row">Fits: ${idea.fit_channels.map(escapeHtml).join(', ')}</div>
                <button class="btn-secondary select-idea-btn" data-idea-id="${idea.id}">Select Idea</button>
            </article>
        `;
    }).join('');

    container.querySelectorAll('.select-idea-btn').forEach((button) => {
        button.addEventListener('click', () => selectIdea(button.dataset.ideaId));
    });
}

function selectIdea(ideaId) {
    state.selectedIdeaId = ideaId;
    const idea = state.ideasPayload.ideas.find((item) => item.id === ideaId);
    document.getElementById('selected-idea-card').className = 'selection-card';
    document.getElementById('selected-idea-card').innerHTML = `
        <strong>${escapeHtml(idea.title)}</strong>
        <span>${escapeHtml(idea.business_impact)}</span>
    `;
    document.getElementById('generate-roadmap-btn').disabled = false;
    renderIdeas(state.ideasPayload);
    appendLog(`Selected ${idea.title}. Choose a mode and generate the roadmap package.`);
    persistState();
}

function buildMarkdownExport(payload) {
    const roadmap = payload.real_world_roadmap;
    const lines = [
        '# AI Hackathon Engine Output',
        '',
        '## 1. Idea Summary',
        `- Problem: ${payload.idea_summary.problem}`,
        `- Selected idea: ${payload.idea_summary.selected_idea.title}`,
        `- Selected mode: ${payload.selected_mode}`,
        '',
        '## 2. Real-World Roadmap',
        `- Where it fits: ${roadmap.where_it_fits.join(', ')}`,
        `- Systems: ${roadmap.integration_points.systems.join(', ')}`,
        `- APIs: ${roadmap.integration_points.apis_required.join(', ')}`,
        `- Data sources: ${roadmap.integration_points.data_sources.join(', ')}`,
        '',
        '## 3. Implementation Phases'
    ];

    roadmap.implementation_phases.forEach((phase) => {
        lines.push(`### ${phase.phase}`);
        lines.push(`- Goal: ${phase.goal}`);
        lines.push(`- Scope: ${phase.scope}`);
        phase.success_metrics.forEach((metric) => lines.push(`- ${metric}`));
        lines.push('');
    });

    lines.push('## 4. Business Impact');
    lines.push(`- Call reduction: ${roadmap.business_impact.call_reduction}`);
    lines.push(`- Time saved: ${roadmap.business_impact.time_saved}`);
    lines.push(`- Cost savings: ${roadmap.business_impact.cost_savings}`);
    lines.push(`- Efficiency gain: ${roadmap.business_impact.efficiency_gain}`);
    lines.push('');

    lines.push('## 5. Practical Feasibility');
    roadmap.practical_feasibility.forEach((item) => lines.push(`- ${item}`));
    lines.push('');

    lines.push('## 6. Risks');
    roadmap.risks.forEach((item) => lines.push(`- ${item}`));
    lines.push('');

    if (payload.prototype) {
        lines.push('## 7. Prototype');
        lines.push(`- Delivery window: ${payload.prototype.delivery_window}`);
        lines.push(`- Stack: ${payload.prototype.stack.join(', ')}`);
        payload.prototype.notes.forEach((item) => lines.push(`- ${item}`));
        lines.push('');
    }

    if (payload.architecture) {
        lines.push('## 7. Architecture');
        lines.push(`- Experience layer: ${payload.architecture.experience_layer.join(', ')}`);
        lines.push(`- AI layer: ${payload.architecture.ai_layer.join(', ')}`);
        lines.push(`- Deployment: ${payload.architecture.deployment.join(', ')}`);
        lines.push('');
    }

    lines.push('## 8. Demo Flow');
    payload.demo_flow.forEach((step, index) => {
        lines.push(`### Step ${index + 1}`);
        lines.push(`- User query: ${step.user_query}`);
        lines.push(`- System action: ${step.system_action}`);
        lines.push(`- Output: ${step.output}`);
        lines.push('');
    });

    lines.push('## 9. PPT Content');
    payload.ppt_content.forEach((slide) => lines.push(`- Slide ${slide.slide}: ${slide.title} - ${slide.content}`));
    lines.push('');

    lines.push('## 10. Video Script');
    payload.video_script.script.forEach((line) => lines.push(`- ${line}`));

    return lines.join('\n');
}

function downloadFile(filename, content, type) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
}

function renderRoadmap(payload) {
    state.roadmapPayload = payload;
    updateExportButtons();
    persistState();
    const roadmap = payload.real_world_roadmap;
    const container = document.getElementById('roadmap-container');
    container.className = 'roadmap-output';

    const prototypeSection = payload.prototype ? `
        <section>
            <h3>Prototype Plan</h3>
            <p><strong>Delivery window:</strong> ${escapeHtml(payload.prototype.delivery_window)}</p>
            <p><strong>Stack:</strong> ${payload.prototype.stack.map(escapeHtml).join(', ')}</p>
            <ul>${payload.prototype.notes.map((note) => `<li>${escapeHtml(note)}</li>`).join('')}</ul>
        </section>
    ` : '';

    const architectureSection = payload.architecture ? `
        <section>
            <h3>Advanced Architecture</h3>
            <p><strong>Experience layer:</strong> ${payload.architecture.experience_layer.map(escapeHtml).join(', ')}</p>
            <p><strong>AI layer:</strong> ${payload.architecture.ai_layer.map(escapeHtml).join(', ')}</p>
            <p><strong>Deployment:</strong> ${payload.architecture.deployment.map(escapeHtml).join(', ')}</p>
        </section>
    ` : '';

    container.innerHTML = `
        <section>
            <h3>1. Idea Summary</h3>
            <p><strong>Selected idea:</strong> ${escapeHtml(payload.idea_summary.selected_idea.title)}</p>
            <p><strong>Selected mode:</strong> ${escapeHtml(payload.selected_mode)}</p>
            <p>${escapeHtml(payload.solution_overview.positioning)}</p>
        </section>
        <section>
            <h3>2. Real-World Roadmap</h3>
            <p><strong>Where it fits:</strong> ${roadmap.where_it_fits.map(escapeHtml).join(', ')}</p>
            <p><strong>Systems:</strong> ${roadmap.integration_points.systems.map(escapeHtml).join(', ')}</p>
            <p><strong>APIs:</strong> ${roadmap.integration_points.apis_required.map(escapeHtml).join(', ')}</p>
            <p><strong>Data sources:</strong> ${roadmap.integration_points.data_sources.map(escapeHtml).join(', ')}</p>
            <div class="phase-list">
                ${roadmap.implementation_phases.map((phase) => `
                    <article class="phase-card">
                        <h4>${escapeHtml(phase.phase)}</h4>
                        <p><strong>Goal:</strong> ${escapeHtml(phase.goal)}</p>
                        <p><strong>Scope:</strong> ${escapeHtml(phase.scope)}</p>
                        <ul>${phase.success_metrics.map((metric) => `<li>${escapeHtml(metric)}</li>`).join('')}</ul>
                    </article>
                `).join('')}
            </div>
        </section>
        <section>
            <h3>3. Business Impact</h3>
            <p><strong>Call reduction:</strong> ${escapeHtml(roadmap.business_impact.call_reduction)}</p>
            <p><strong>Time saved:</strong> ${escapeHtml(roadmap.business_impact.time_saved)}</p>
            <p><strong>Cost savings:</strong> ${escapeHtml(roadmap.business_impact.cost_savings)}</p>
            <p><strong>Efficiency gain:</strong> ${escapeHtml(roadmap.business_impact.efficiency_gain)}</p>
        </section>
        <section>
            <h3>4. Practical Feasibility</h3>
            <ul>${roadmap.practical_feasibility.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>
        </section>
        <section>
            <h3>5. Risks</h3>
            <ul>${roadmap.risks.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>
        </section>
        ${prototypeSection}
        ${architectureSection}
        <section>
            <h3>6. Demo Flow</h3>
            ${payload.demo_flow.map((step) => `
                <article class="demo-card">
                    <p><strong>User query:</strong> ${escapeHtml(step.user_query)}</p>
                    <p><strong>System action:</strong> ${escapeHtml(step.system_action)}</p>
                    <p><strong>Output:</strong> ${escapeHtml(step.output)}</p>
                </article>
            `).join('')}
        </section>
        <section>
            <h3>7. PPT Content</h3>
            <div class="slide-list">
                ${payload.ppt_content.map((slide) => `
                    <article class="slide-card">
                        <strong>Slide ${slide.slide}: ${escapeHtml(slide.title)}</strong>
                        <p>${escapeHtml(slide.content)}</p>
                    </article>
                `).join('')}
            </div>
        </section>
        <section>
            <h3>8. Video Script</h3>
            <p><strong>Duration:</strong> ${escapeHtml(payload.video_script.duration)}</p>
            <ul>${payload.video_script.script.map((line) => `<li>${escapeHtml(line)}</li>`).join('')}</ul>
        </section>
    `;
}

async function readNdjsonStream(response, handlers) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const { value, done } = await reader.read();
        if (done) {
            break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
            if (!line.trim()) {
                continue;
            }
            const event = JSON.parse(line);
            handlers(event);
        }
    }
}

async function generateIdeas() {
    const problemStatement = document.getElementById('problem-statement').value.trim();
    if (problemStatement.length < 20) {
        appendLog('Add a fuller problem statement before generating ideas.');
        setStatus('Needs Input', 'warning');
        return;
    }

    setStatus('Generating', 'working');
    appendLog('Starting real-time idea generation.');
    document.getElementById('generate-roadmap-btn').disabled = true;
    document.getElementById('selected-idea-card').className = 'selection-card muted-card';
    document.getElementById('selected-idea-card').textContent = 'No idea selected yet.';
    state.ideasPayload = null;
    state.selectedIdeaId = null;
    state.roadmapPayload = null;
    updateExportButtons();
    persistState();
    setRoadmapPlaceholder('Idea generation is in progress.');

    const response = await fetch('/api/hackathon-engine/generate-stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ problem_statement: problemStatement })
    });

    if (!response.ok) {
        const payload = await response.json();
        appendLog(payload.detail || 'Idea generation failed.');
        setStatus('Failed', 'error');
        return;
    }

    await readNdjsonStream(response, (event) => {
        if (event.type === 'status') {
            appendLog(event.data.message);
        }
        if (event.type === 'ideas') {
            renderIdeas(event.data);
            const recommended = event.data.ideas.find((idea) => idea.id === event.data.recommended_idea_id);
            appendLog(`Top recommendation is ${recommended.title}.`);
        }
        if (event.type === 'done') {
            setStatus('Ideas Ready', 'success');
        }
    });
}

async function generateRoadmap() {
    if (!state.ideasPayload || !state.selectedIdeaId) {
        appendLog('Select an idea before generating the roadmap package.');
        setStatus('Selection Needed', 'warning');
        return;
    }

    setStatus('Building', 'working');
    appendLog('Generating roadmap, demo, PPT, and video content.');
    setRoadmapPlaceholder('Generating roadmap package...');

    const response = await fetch('/api/hackathon-engine/roadmap-stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            problem_statement: document.getElementById('problem-statement').value.trim(),
            selected_idea_id: state.selectedIdeaId,
            mode: state.selectedMode,
            ideas: state.ideasPayload.ideas
        })
    });

    if (!response.ok) {
        const payload = await response.json();
        appendLog(payload.detail || 'Roadmap generation failed.');
        setStatus('Failed', 'error');
        return;
    }

    await readNdjsonStream(response, (event) => {
        if (event.type === 'status') {
            appendLog(event.data.message);
        }
        if (event.type === 'roadmap') {
            renderRoadmap(event.data);
        }
        if (event.type === 'done') {
            appendLog('Roadmap package complete.');
            setStatus('Package Ready', 'success');
        }
    });
}

function resetSession() {
    localStorage.removeItem(STORAGE_KEY);
    state.ideasPayload = null;
    state.selectedIdeaId = null;
    state.selectedMode = 'roadmap';
    state.roadmapPayload = null;
    document.getElementById('problem-statement').value = '';
    document.getElementById('selected-idea-card').className = 'selection-card muted-card';
    document.getElementById('selected-idea-card').textContent = 'No idea selected yet.';
    document.getElementById('ideas-container').className = 'ideas-grid empty-state';
    document.getElementById('ideas-container').textContent = 'Ranked solution ideas will appear here.';
    document.getElementById('generate-roadmap-btn').disabled = true;
    document.getElementById('recommendation-pill').classList.add('hidden');
    setRoadmapPlaceholder('Generate ideas first, then select one to create the full package.');
    document.querySelectorAll('.mode-btn').forEach((item) => item.classList.toggle('active', item.dataset.mode === 'roadmap'));
    document.getElementById('live-log').innerHTML = '<div class="log-item">Waiting for a problem statement.</div>';
    setStatus('Idle', 'idle');
}

function restoreSession() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (!saved) {
        updateExportButtons();
        return;
    }

    try {
        const payload = JSON.parse(saved);
        document.getElementById('problem-statement').value = payload.problemStatement || '';
        state.selectedMode = payload.selectedMode || 'roadmap';
        state.selectedIdeaId = payload.selectedIdeaId || null;
        state.ideasPayload = payload.ideasPayload || null;
        state.roadmapPayload = payload.roadmapPayload || null;
        document.querySelectorAll('.mode-btn').forEach((item) => item.classList.toggle('active', item.dataset.mode === state.selectedMode));

        if (state.ideasPayload) {
            renderIdeas(state.ideasPayload);
            if (state.selectedIdeaId) {
                selectIdea(state.selectedIdeaId);
            }
        }

        if (state.roadmapPayload) {
            renderRoadmap(state.roadmapPayload);
            appendLog('Restored previous roadmap package from saved session.');
            setStatus('Restored', 'success');
        } else if (state.ideasPayload) {
            appendLog('Restored saved ideas and selection state.');
            setStatus('Ideas Ready', 'success');
        } else {
            updateExportButtons();
        }
    } catch (error) {
        console.error('Failed to restore session', error);
        localStorage.removeItem(STORAGE_KEY);
        updateExportButtons();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('generate-ideas-btn').addEventListener('click', generateIdeas);
    document.getElementById('generate-roadmap-btn').addEventListener('click', generateRoadmap);
    document.getElementById('reset-session-btn').addEventListener('click', resetSession);
    document.getElementById('export-json-btn').addEventListener('click', () => {
        if (!state.roadmapPayload) {
            return;
        }
        downloadFile('hackathon-engine-output.json', JSON.stringify(state.roadmapPayload, null, 2), 'application/json');
    });
    document.getElementById('export-md-btn').addEventListener('click', () => {
        if (!state.roadmapPayload) {
            return;
        }
        downloadFile('hackathon-engine-output.md', buildMarkdownExport(state.roadmapPayload), 'text/markdown');
    });
    document.getElementById('problem-statement').addEventListener('input', persistState);

    document.querySelectorAll('.mode-btn').forEach((button) => {
        button.addEventListener('click', () => {
            document.querySelectorAll('.mode-btn').forEach((item) => item.classList.remove('active'));
            button.classList.add('active');
            state.selectedMode = button.dataset.mode;
            appendLog(`Mode selected: ${button.textContent}.`);
            persistState();
        });
    });

    restoreSession();
    updateExportButtons();
});