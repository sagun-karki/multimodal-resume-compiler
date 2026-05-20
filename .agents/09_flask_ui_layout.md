# WEB DASHBOARD SPECIFICATION: MONITORING & CONTROL CANVAS

## 1. Interface Grid Layout
The application interface is a responsive side-by-side terminal monitoring dashboard styled with premium Vanilla CSS.
- **Left Panel (Width: Resizable)**: Contains input parameters, markdown editors, live telemetry dashboard, and real-time streaming execution logs.
- **Right Panel (Width: Resizable)**: Visual canvas that loads the compiled PDF preview frame.
- **Interactive Splitters**:
  - `#main-resizer`: Draggable vertical splitter to resize left-right panel ratio (constrained between 20% and 80%).
  - `#terminal-resizer`: Draggable horizontal splitter to resize terminal viewport height (constrained between 60px and 450px).

## 2. Interactive Components

### A. Dual Markdown Editor Tabs
- **Job Description Tab**: Input textarea to insert target job listings.
- **User Profile Tab**: Live-editable textarea showing `my-content/user_profile.md` data.

### B. Target Keywords Pills (Interactive)
- Compares job listing and profile text, displaying target keyword pills.
- **Click to Toggle**: Clicking keyword pills dynamically switches their active/inactive status and updates the optimization context, allowing users to prioritize specific skills.

### C. Live Chart.js Diagnostics
- **Keyword Match Distribution (Donut Chart)**: Visualizes the proportion of matched vs. unmatched keywords. Re-calculates and re-renders dynamically as keyword pills are toggled.
- **Token Utilization Ratio (Pie Chart)**: Logs token telemetry in real-time (Input vs. Output tokens) to track compilation costs.

### D. The Streaming Execution Terminal
- Receives logs from the backend via Server-Sent Events (SSE) `/api/stream`.
- Displays real-time progress indicators: `[ATS Analyzer Agent]`, `[Resume Writer Agent]`, `[Compiler Tool]`, `[Visual Auditor Agent]`.

### E. Dynamic PDF Canvas
- The right-hand column hosts an iframe targeting the compiled PDF.
- When compilation succeeds, the client receives a reload signal and updates the iframe's `src` with a cache-busting timestamp (`/output/resume.pdf?t=TIMESTAMP`), reloading the PDF document seamlessly.
