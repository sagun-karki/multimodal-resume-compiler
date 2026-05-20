let eventSource = null;

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
        document.getElementById('diagnostic-strengths').innerHTML = '';
        document.getElementById('diagnostic-gaps').innerHTML = '';
    }
    
    addLog(action === 'analyze' ? "Executing Stage 0: Gap Analyzer..." : "Executing Auto-Correction Loop...", "SYS");

    eventSource = new EventSource(`/stream?action=${action}`);

    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);
        
        let logType = 'INFO';
        if (data.status === 'success') logType = 'SUCCESS';
        if (data.status === 'error') logType = 'ERROR';
        if (data.status === 'warning') logType = 'SYS';

        addLog(data.message, logType);
        
        if (data.status === 'success' && data.stage === 0 && data.gap_report) {
            const report = data.gap_report;
            document.getElementById('diagnostic-container').style.display = 'block';
            document.getElementById('diagnostic-score').innerText = `${report.closeness_score}% MATCH`;
            
            const strContainer = document.getElementById('diagnostic-strengths');
            strContainer.innerHTML = '';
            if (report.matching_strengths) {
                report.matching_strengths.forEach(item => {
                    const div = document.createElement('div');
                    div.className = 'ats-item-strength';
                    div.innerText = `+ ${item}`;
                    strContainer.appendChild(div);
                });
            }

            const gapsContainer = document.getElementById('diagnostic-gaps');
            gapsContainer.innerHTML = '';
            if (report.critical_gaps) {
                report.critical_gaps.forEach(item => {
                    const div = document.createElement('div');
                    div.className = 'ats-item-gap';
                    div.innerHTML = `<span>- ${item}</span><span class="ats-inject-label">INJECT</span>`;
                    div.onclick = () => injectKeyword(item);
                    gapsContainer.appendChild(div);
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
