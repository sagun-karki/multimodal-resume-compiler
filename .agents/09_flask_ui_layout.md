# INTERFACE SPECIFICATION: DUAL-PANEL MONITORING CANVAS

The application UI must be implemented as a responsive side-by-side terminal monitoring dashboard using Tailwind CSS.

## 1. Layout Structure
- **Global Frame:** Fixed full-screen display (`h-screen overflow-hidden`), slate-dark or dark-mode industrial theme.
- **Left Column (Width: 45%):** Input parameters, live token telemetry telemetry, and real-time streaming execution logs.
- **Right Column (Width: 55%):** An interactive viewport canvas rendering the generated layout.

## 2. Component Layout & Logic

### A. The Input Box & Controls (Top Left)
- Textarea block to paste raw target Job Descriptions.
- An execution action button (`Run Optimization Loop`). Clicking this fires an asynchronous processing request to `/api/optimize` via Server-Sent Events (SSE).

### B. Live Token Telemetry Panel (Mid Left)
A dashboard interface presenting running metrics:
- **Closeness Score:** Visual progress bar updated when Stage 0 responds.
- **Token Counters:** High-visibility text readout splitting `Input Tokens` and `Output Tokens`.
- **Financial Tracker:** Live cost calculation utilizing strict metric coefficients:
  - Text Models (e.g., gpt-4o-mini): Input = \$0.15 / 1M, Output = \$0.60 / 1M
  - Vision Models (e.g., gpt-4o): Input = \$2.50 / 1M, Output = \$10.00 / 1M

### C. The Stage Execution Terminal (Bottom Left)
- A terminal styling window (`bg-black text-green-400 font-mono`) that appends detailed execution streams from the Flask server.
- Each time a stage completes, it must append its action trace along with its isolated token footprint (e.g., `[Round 2] Stage 1 Completed. +1,450 output tokens`).

### D. The Visual Document Canvas (Right Column)
- On web-app boot, it reads and displays a default pre-compiled PNG of the baseline template.
- **Dynamic Live Reload:** The frontend must listen for a specific event stream from the SSE endpoint: `event: page_update`. When received, it updates the source attribute of the display image placeholder using a cache-busting timestamp query parameter (`/api/view_resume.png?t=TIMESTAMP`). This allows the developer to watch the resume physically adapt and resize in real-time.

---

# CODE BLUEPRINT: MINIMAL FLASK APP ENGINE

Implement this foundational execution architecture inside `app.py`. Keep code cohesive, clean, and focus heavily on execution streaming stability.

```python
import json
import time
from flask import Flask, render_template, Response, request, send_file

app = Flask(__name__)

# System-wide state tracking telemetry dictionaries
telemetry = {
    "input_tokens": 0,
    "output_tokens": 0,
    "accumulated_cost": 0.0,
    "closeness_score": 0
}

@app.route("/")
def index():
    # Render main dashboard view
    return render_template("index.html")

@app.route("/api/view_resume.png")
def view_resume():
    # Serves the latest rasterized image file from the output cache directory
    return send_file("output/resume.png", mimetype="image/png")

@app.route("/api/optimize", methods=["POST"])
def optimize():
    jd_text = request.json.get("job_description", "")
    
    def event_stream():
        global telemetry
        # Reset trackers for a new run
        telemetry = {"input_tokens": 0, "output_tokens": 0, "accumulated_cost": 0.0, "closeness_score": 0}
        
        # STAGE 0 EXECUTION
        yield f"data: {json.dumps({'log': '🤖 [Stage 0] Analyzing Job Description Alignment...', 'telemetry': telemetry})}\n\n"
        time.sleep(1) # Yield execution window breathing room
        
        # Mock calculation updating metrics step
        telemetry["closeness_score"] = 72
        telemetry["input_tokens"] += 2500
        telemetry["accumulated_cost"] += (2500 / 1000000) * 0.15
        
        yield f"data: {json.dumps({'log': '✅ [Stage 0] Done. Score: 72%. Gaps identified.', 'telemetry': telemetry})}\n\n"
        
        # LOOP SIMULATION RUN (STAGES 1 - 5)
        for round_idx in range(1, 4):
            yield f"data: {json.dumps({'log': f'🔄 [Round {round_idx}] Stage 1: Compiling LaTeX Data...', 'telemetry': telemetry})}\n\n"
            time.sleep(1)
            
            # Local compilation simulation tasks (Stage 2 & 3 cost 0 tokens)
            yield f"data: {json.dumps({'log': f'⚙️ [Round {round_idx}] Stage 3: Running XeLaTeX Subprocess...', 'telemetry': telemetry})}\n\n"
            time.sleep(1)
            
            # Stage 4 image reload trigger
            yield f"event: page_update\ndata: reload\n\n"
            
            # Stage 5 evaluation simulation
            telemetry["input_tokens"] += 915 # Standard Vision high-detail tile cost
            telemetry["accumulated_cost"] += (915 / 1000000) * 2.50
            
            if round_idx < 3:
                yield f"data: {json.dumps({'log': f'⚠️ [Round {round_idx}] Stage 5 Vision: EMPTY_BOTTOM detected. Appending data...', 'telemetry': telemetry})}\n\n"
            else:
                yield f"data: {json.dumps({'log': '🎉 [Round 3] Stage 5 Vision: STATUS: PERFECT. Loop Converged!', 'telemetry': telemetry})}\n\n"
                
    return Response(event_stream(), mimetype="text/event-stream")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
```

## UI Implementation Target Blueprint (`templates/index.html`)

The frontend dashboard script must parse the event streams using standard EventSource structures:

```javascript
const source = new EventSource('/api/optimize');

// Listen for standard data text streaming logs
source.onmessage = function(event) {
    const data = JSON.parse(event.data);
    document.getElementById('terminal-log').innerHTML += `<div>${data.log}</div>`;
    document.getElementById('cost-metric').innerText = `$${data.telemetry.accumulated_cost.toFixed(4)}`;
    document.getElementById('score-bar').style.width = `${data.telemetry.closeness_score}%`;
};

// Listen for explicit custom canvas updates to break rendering cache
source.addEventListener('page_update', function(e) {
    document.getElementById('resume-canvas').src = `/api/view_resume.png?t=${new Date().getTime()}`;
});
```
