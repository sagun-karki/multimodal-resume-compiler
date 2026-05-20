let eventSource = null;
let chartKeywords = null;
let chartTokens = null;
const sectionIdMap = new Map();

function toSafeSectionId(name) {
    return String(name || "")
        .toLowerCase()
        .replace(/[^a-z0-9_-]+/g, "-")
        .replace(/^-+|-+$/g, "") || "section";
}

function renderKeywordChart(matchingCount, gapsCount) {
    const ctx = document.getElementById('chart-keywords').getContext('2d');
    if (chartKeywords) chartKeywords.destroy();
    
    chartKeywords = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Target Active', 'Target Inactive'],
            datasets: [{
                data: [matchingCount, gapsCount],
                backgroundColor: ['rgba(20, 184, 166, 0.75)', 'rgba(255, 255, 255, 0.05)'],
                borderColor: '#141414',
                borderWidth: 1.5,
                hoverBackgroundColor: ['rgba(20, 184, 166, 0.9)', 'rgba(255, 255, 255, 0.1)']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: '#888888',
                        boxWidth: 8,
                        padding: 6,
                        font: {
                            family: 'Fira Code',
                            size: 8
                        }
                    }
                }
            },
            cutout: '70%'
        }
    });
}

function renderTokenChart(inputTokens, outputTokens) {
    const ctx = document.getElementById('chart-tokens').getContext('2d');
    if (chartTokens) chartTokens.destroy();
    
    chartTokens = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['Input', 'Output'],
            datasets: [{
                data: [inputTokens, outputTokens],
                backgroundColor: ['rgba(84, 200, 255, 0.7)', 'rgba(81, 207, 102, 0.7)'],
                borderColor: '#141414',
                borderWidth: 1.5,
                hoverBackgroundColor: ['rgba(84, 200, 255, 0.9)', 'rgba(81, 207, 102, 0.9)']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: '#888888',
                        boxWidth: 8,
                        padding: 6,
                        font: {
                            family: 'Fira Code',
                            size: 8
                        }
                    }
                }
            }
        }
    });
}

function switchTab(tab) {
    document.getElementById('tab-job').classList.remove('active');
    document.getElementById('tab-profile').classList.remove('active');
    document.getElementById('editor-job').classList.remove('active');
    document.getElementById('editor-profile').classList.remove('active');

    if (tab === 'job') {
        document.getElementById('tab-job').classList.add('active');
        document.getElementById('editor-job').classList.add('active');
    } else {
        document.getElementById('tab-profile').classList.add('active');
        document.getElementById('editor-profile').classList.add('active');
    }
}

function switchFormat(format) {
    document.getElementById('btn-pdf').classList.remove('active');
    document.getElementById('btn-png').classList.remove('active');
    document.getElementById('pdf-frame').style.display = 'none';
    document.getElementById('png-frame').style.display = 'none';

    if (format === 'pdf') {
        document.getElementById('btn-pdf').classList.add('active');
        document.getElementById('pdf-frame').style.display = 'block';
        addLog('Output payload pipeline changed to VECTOR_PDF.', 'RENDERER');
    } else {
        document.getElementById('btn-png').classList.add('active');
        document.getElementById('png-frame').style.display = 'block';
        addLog('Output payload pipeline changed to RASTER_PNG.', 'RENDERER');
    }
}



function addLog(text, type = 'INFO') {
    const time = new Date().toLocaleTimeString('en-US', { hour12: false });
    const container = document.getElementById('terminal-logs');
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    
    let typeClass = 'log-type-info';
    if (type === 'SYS') typeClass = 'log-type-sys';
    if (type === 'MUTATOR') typeClass = 'log-type-mutator';
    if (type === 'RENDERER') typeClass = 'log-type-renderer';
    if (type === 'SUCCESS') typeClass = 'log-type-success';
    if (type === 'ERROR') typeClass = 'log-type-error';

    entry.innerHTML = `
        <span class="log-time">${time}</span>
        <span class="log-type ${typeClass}">${type}</span>
        <span style="word-break: break-all;">${text.replace(/\n/g, '<br>')}</span>
    `;
    container.appendChild(entry);
    container.scrollTop = container.scrollHeight;
}

function endOptimization() {
    document.getElementById('compile-btn').disabled = false;
    document.getElementById('stop-btn').style.display = 'none';
    document.getElementById('stop-btn').disabled = false;
}

async function stopOptimization() {
    document.getElementById('stop-btn').disabled = true;
    addLog("Sending cancellation request to compile pipeline...", "SYS");
    try {
        await fetch('/api/cancel', { method: 'POST' });
    } catch (err) {
        console.error("Failed to call cancel API", err);
    }
}

async function runPipeline(action) {
    const compileBtn = document.getElementById('compile-btn');
    const proceedBtn = document.getElementById('proceed-btn');
    const stopBtn = document.getElementById('stop-btn');
    
    const profile = document.getElementById('profile-editor').value;
    const jd = document.getElementById('jd-editor').value;
    
    compileBtn.disabled = true;
    proceedBtn.style.display = 'none';
    stopBtn.style.display = 'inline-block';
    stopBtn.disabled = false;
    addLog("Saving workspace configs...", "SYS");

    try {
        const saveRes = await fetch('/api/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ profile, job_description: jd })
        });
        const saveResult = await saveRes.json();
        if (saveResult.status !== 'success') {
            addLog(`Error saving content: ${saveResult.message}`, "ERROR");
            endOptimization();
            return;
        }
    } catch (err) {
        addLog(`Failed to save API: ${err}`, "ERROR");
        endOptimization();
        return;
    }

    if (eventSource) eventSource.close();

    if (action === 'analyze') {
        document.getElementById('terminal-logs').innerHTML = '';
        document.getElementById('diagnostic-container').style.display = 'none';
    }
    
    addLog(action === 'analyze' ? "Executing Stage 0: Gap Analyzer..." : "Executing Auto-Correction Loop...", "SYS");

    let url = `/stream?action=${action}`;
    if (action === 'optimize') {
        if (window.activeKeywords) {
            url += `&keywords=${encodeURIComponent(JSON.stringify(Array.from(window.activeKeywords)))}`;
        }
        if (window.activeSections) {
            const allCheckboxes = Array.from(document.querySelectorAll("[id^='chk-sec-']"));
            const allSections = allCheckboxes
                .map((el) => sectionIdMap.get(el.id))
                .filter(Boolean);
            const skippedSections = allSections.filter(sec => !window.activeSections.has(sec));
            url += `&skipped_sections=${encodeURIComponent(JSON.stringify(skippedSections))}`;
        }
    }
    eventSource = new EventSource(url);

    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);
        
        let logType = 'INFO';
        if (data.status === 'success') logType = 'SUCCESS';
        if (data.status === 'error') logType = 'ERROR';
        if (data.status === 'warning') logType = 'SYS';

        addLog(data.message, logType);

        if (data.telemetry) {
            renderTokenChart(data.telemetry.input_tokens || 0, data.telemetry.output_tokens || 0);
        }
        
        if (data.status === 'success' && data.stage === 0 && data.gap_report) {
            const report = data.gap_report;
            document.getElementById('diagnostic-container').style.display = 'block';
            document.getElementById('diagnostic-score').innerText = `${report.closeness_score}% MATCH`;
            
            // Show charts container
            document.getElementById('diagnostic-charts').style.display = 'grid';
            const matchedCount = (report.matching_strengths || []).length;
            const gapsCount = (report.critical_gaps || []).length;
            renderKeywordChart(matchedCount, gapsCount);
            
            // Render Target Keyword Pills
            const pillsContainer = document.getElementById('diagnostic-pills');
            const pillsLabel = document.getElementById('diagnostic-pills-label');
            pillsContainer.innerHTML = '';
            
            const keywords = Array.from(new Set([
                ...(report.critical_gaps || []),
                ...(report.target_keywords || [])
            ]));
            
            window.activeKeywords = new Set(keywords);
            
            if (keywords.length > 0) {
                pillsLabel.style.display = 'block';
                keywords.forEach(item => {
                    const btn = document.createElement('button');
                    btn.className = 'ats-pill active';
                    
                    function updatePillStyle(pill, active) {
                        if (active) {
                            pill.style.cssText = "background: rgba(20, 184, 166, 0.15); border: 1px solid rgba(20, 184, 166, 0.4); color: #14b8a6; padding: 4px 8px; font-size: 10px; font-family: 'Fira Code', monospace; border-radius: 2px; cursor: pointer; display: flex; align-items: center; gap: 4px; transition: all 0.2s;";
                            pill.innerHTML = `<span>✓ ${item}</span>`;
                        } else {
                            pill.style.cssText = "background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); color: #888; padding: 4px 8px; font-size: 10px; font-family: 'Fira Code', monospace; border-radius: 2px; cursor: pointer; display: flex; align-items: center; gap: 4px; transition: all 0.2s;";
                            pill.innerHTML = `<span>✗ ${item}</span>`;
                        }
                    }
                    
                    updatePillStyle(btn, true);
                    
                    btn.onclick = () => {
                        if (window.activeKeywords.has(item)) {
                            window.activeKeywords.delete(item);
                            updatePillStyle(btn, false);
                        } else {
                            window.activeKeywords.add(item);
                            updatePillStyle(btn, true);
                        }
                        
                        // Update matching chart dynamically as pills are toggled
                        const activeCount = window.activeKeywords.size;
                        const inactiveCount = keywords.length - activeCount;
                        renderKeywordChart(activeCount, inactiveCount);
                    };
                    pillsContainer.appendChild(btn);
                });
            } else {
                pillsLabel.style.display = 'none';
            }

            // Render Section-by-Section Cards
            const sectionsContainer = document.getElementById('diagnostic-sections');
            sectionsContainer.innerHTML = '';
            if (report.sections_analysis) {
                window.activeSections = window.activeSections || new Set();
                
                Object.entries(report.sections_analysis).forEach(([secName, secData]) => {
                    window.activeSections.add(secName);
                    const safeSecId = `chk-sec-${toSafeSectionId(secName)}`;
                    sectionIdMap.set(safeSecId, secName);
                    
                    const card = document.createElement('div');
                    card.className = 'section-card';
                    card.style.cssText = "border: 1px solid var(--border-color); background: #1a1a1a; padding: 12px; border-radius: 4px; display: flex; flex-direction: column; gap: 8px; transition: all 0.2s;";
                    
                    let bulletHtml = '';
                    if (secData.add && secData.add.length > 0) {
                        bulletHtml += `<div style="color: var(--accent-green)">+ ADD: ${secData.add.join(', ')}</div>`;
                    }
                    if (secData.remove && secData.remove.length > 0) {
                        bulletHtml += `<div style="color: var(--accent-red)">- REMOVE: ${secData.remove.join(', ')}</div>`;
                    }
                    if (secData.update && secData.update.length > 0) {
                        bulletHtml += `<div style="color: var(--accent-blue)">* UPDATE: ${secData.update.join(', ')}</div>`;
                    }

                    card.innerHTML = `
                        <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #2d2d2d; padding-bottom: 4px;">
                            <span style="font-family: 'Fira Code', monospace; font-size: 11px; font-weight: 700; color: var(--text-main); text-transform: uppercase;">
                                ${secName}
                            </span>
                            <label style="display: flex; align-items: center; gap: 4px; font-size: 10px; font-family: 'Fira Code', monospace; color: #888; cursor: pointer; user-select: none;">
                                <input type="checkbox" id="${safeSecId}" checked style="accent-color: #14b8a6; cursor: pointer;">
                                OPTIMIZE
                            </label>
                        </div>
                        <p style="font-size: 11px; color: var(--text-muted); line-height: 1.4; margin: 0;">
                            ${secData.recommendation || ''}
                        </p>
                        ${bulletHtml ? `<div style="display: flex; flex-direction: column; gap: 4px; font-size: 10px; font-family: 'Fira Code', monospace; margin-top: 4px;">${bulletHtml}</div>` : ''}
                    `;
                    sectionsContainer.appendChild(card);

                    const chk = card.querySelector(`#${safeSecId}`);
                    chk.onchange = (e) => {
                        if (e.target.checked) {
                            window.activeSections.add(secName);
                            card.style.opacity = '1';
                        } else {
                            window.activeSections.delete(secName);
                            card.style.opacity = '0.5';
                        }
                    };
                });
            }
        } else if (data.status === 'error') {
            eventSource.close();
            endOptimization();
        } else if (data.status === 'complete') {
            if (action === 'analyze') {
                proceedBtn.style.display = 'inline-block';
            } else {
                const timestamp = new Date().getTime();
                document.getElementById('pdf-frame').src = `/output/resume.pdf?t=${timestamp}`;
                document.getElementById('png-frame').src = `/output/resume.png?t=${timestamp}`;
            }
            eventSource.close();
            endOptimization();
        }
    };

    eventSource.onerror = function(err) {
        addLog("SSE Connection error. Pipeline compilation stream closed.", "ERROR");
        eventSource.close();
        endOptimization();
    };
}

function startAnalysis() { runPipeline('analyze'); }
function startOptimization() { runPipeline('optimize'); }

function injectKeyword(term) {
    addLog(`Injecting [${term}] to Profile Skills.`, 'MUTATOR');
    const editor = document.getElementById('profile-editor');
    let content = editor.value;
    const skillsHeader = '## SKILLS';
    const lines = content.split('\n');
    const skillsIndex = lines.findIndex(line => line.toUpperCase().includes(skillsHeader));

    if (skillsIndex !== -1) {
        let insertIndex = skillsIndex + 1;
        while (insertIndex < lines.length && lines[insertIndex].trim() !== '' && !lines[insertIndex].startsWith('#')) {
            insertIndex++;
        }
        const lastLine = lines[insertIndex - 1];
        if (lastLine && lastLine.startsWith('- ')) {
            lines[insertIndex - 1] = `${lastLine}, ${term}`;
        } else {
            lines.splice(insertIndex, 0, `- Focus Area: ${term}`);
        }
        editor.value = lines.join('\n');
    } else {
        editor.value += `\n\n## SKILLS\n- ${term}`;
    }
    addLog(`Injection complete. Please review.`, 'MUTATOR');
    
    // Switch to profile tab to show injection
    switchTab('profile');
}

// --- Panel Resizing Engine ---
document.addEventListener('DOMContentLoaded', () => {
    // Left-Right Main Resizer
    const mainResizer = document.getElementById('main-resizer');
    const leftPanel = document.querySelector('.left-panel');
    const rightPanel = document.querySelector('.right-panel');
    
    let isResizingH = false;
    
    if (mainResizer && leftPanel && rightPanel) {
        mainResizer.addEventListener('mousedown', (e) => {
            isResizingH = true;
            mainResizer.classList.add('active');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
            
            const pdfFrame = document.getElementById('pdf-frame');
            if (pdfFrame) pdfFrame.style.pointerEvents = 'none';
        });
        
        document.addEventListener('mousemove', (e) => {
            if (!isResizingH) return;
            
            const mainElement = document.querySelector('main');
            if (!mainElement) return;
            
            const containerWidth = mainElement.getBoundingClientRect().width;
            let newLeftWidth = (e.clientX / containerWidth) * 100;
            
            // Boundaries constraints
            if (newLeftWidth < 20) newLeftWidth = 20;
            if (newLeftWidth > 80) newLeftWidth = 80;
            
            leftPanel.style.width = `${newLeftWidth}%`;
            rightPanel.style.width = `${100 - newLeftWidth}%`;
        });
        
        document.addEventListener('mouseup', () => {
            if (isResizingH) {
                isResizingH = false;
                mainResizer.classList.remove('active');
                document.body.style.cursor = 'default';
                document.body.style.userSelect = 'auto';
                
                const pdfFrame = document.getElementById('pdf-frame');
                if (pdfFrame) pdfFrame.style.pointerEvents = 'auto';
            }
        });
    }

    // Top-Bottom Terminal Resizer
    const terminalResizer = document.getElementById('terminal-resizer');
    const terminal = document.querySelector('.terminal');
    
    let isResizingV = false;
    
    if (terminalResizer && terminal) {
        terminalResizer.addEventListener('mousedown', (e) => {
            isResizingV = true;
            terminalResizer.classList.add('active');
            document.body.style.cursor = 'row-resize';
            document.body.style.userSelect = 'none';
            
            const pdfFrame = document.getElementById('pdf-frame');
            if (pdfFrame) pdfFrame.style.pointerEvents = 'none';
        });
        
        document.addEventListener('mousemove', (e) => {
            if (!isResizingV) return;
            
            const leftPanelRect = leftPanel.getBoundingClientRect();
            const newHeight = leftPanelRect.bottom - e.clientY;
            
            // Constraints
            if (newHeight >= 60 && newHeight <= 450) {
                terminal.style.height = `${newHeight}px`;
            }
        });
        
        document.addEventListener('mouseup', () => {
            if (isResizingV) {
                isResizingV = false;
                terminalResizer.classList.remove('active');
                document.body.style.cursor = 'default';
                document.body.style.userSelect = 'auto';
                
                const pdfFrame = document.getElementById('pdf-frame');
                if (pdfFrame) pdfFrame.style.pointerEvents = 'auto';
            }
        });
    }
});
