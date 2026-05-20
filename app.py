import os
import json
from flask import Flask, render_template, request, jsonify, Response, send_from_directory
from dotenv import load_dotenv

# Load API keys from .env if present
load_dotenv()

from utils.context import PipelineContext
from stages.orchestrator import run_optimization_pipeline

app = Flask(__name__)

# Base Directories
WORKSPACE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(WORKSPACE, "my-content")
RESOURCES_DIR = os.path.join(WORKSPACE, "resources")
OUTPUT_DIR = os.path.join(WORKSPACE, "output")

# File Paths
PROFILE_PATH = os.path.join(CONTENT_DIR, "user_profile.md")
JD_PATH = os.path.join(CONTENT_DIR, "job_description.txt")
MAIN_TEX_PATH = os.path.join(RESOURCES_DIR, "resume.tex")
GENERATED_TEX_PATH = os.path.join(RESOURCES_DIR, "generated_data.tex")

# Ensure required directories exist
os.makedirs(CONTENT_DIR, exist_ok=True)
os.makedirs(RESOURCES_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Ensure initial PDF and PNG are generated if missing
pdf_file = os.path.join(OUTPUT_DIR, "resume.pdf")
png_file = os.path.join(OUTPUT_DIR, "resume.png")
if not os.path.exists(pdf_file) or not os.path.exists(png_file):
    print("[app.py] Initial resume PDF or PNG not found. Compiling default version...")
    try:
        from stages.stage2_pdf_manager import run_stage2
        # Compile resume and rasterize
        success, err, _ = run_stage2(MAIN_TEX_PATH, OUTPUT_DIR)
        if success:
            print("[app.py] Initial compilation successful.")
        else:
            print(f"[app.py] Initial compilation failed: {err}")
    except Exception as e:
        print(f"[app.py] Error during initial compilation: {str(e)}")

@app.route("/")
def index():
    """
    Serve main dashboard layout.
    """
    # Load default data to display in editor textareas
    profile_content = ""
    if os.path.exists(PROFILE_PATH):
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            profile_content = f.read()

    jd_content = ""
    if os.path.exists(JD_PATH):
        with open(JD_PATH, "r", encoding="utf-8") as f:
            jd_content = f.read()

    return render_template("index.html", profile=profile_content, job_description=jd_content)

@app.route("/api/save", methods=["POST"])
def save_inputs():
    """
    Saves the user's updated profile and job description from the UI editors.
    """
    data = request.json
    profile_text = data.get("profile", "")
    jd_text = data.get("job_description", "")

    try:
        with open(PROFILE_PATH, "w", encoding="utf-8") as f:
            f.write(profile_text)
        with open(JD_PATH, "w", encoding="utf-8") as f:
            f.write(jd_text)
        return jsonify({"status": "success", "message": "Content files saved successfully."})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to save content: {str(e)}"}), 500

PIPELINE_CANCELLED = False

@app.route("/api/cancel", methods=["POST"])
def cancel_pipeline():
    global PIPELINE_CANCELLED
    PIPELINE_CANCELLED = True
    return jsonify({"status": "success", "message": "Cancellation request received."})

@app.route("/stream")
def compile_stream():
    """
    Server-Sent Events endpoint to stream resume compilation logs in real time.
    """
    global PIPELINE_CANCELLED
    PIPELINE_CANCELLED = False

    action = request.args.get("action", "all")

    # Verify Gemini API key is set
    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        def error_stream():
            yield "data: " + json.dumps({
                "status": "error",
                "message": "API_KEY_ERROR: GEMINI_API_KEY or GOOGLE_API_KEY environment variable is not set. Please set your API key in the environment or .env file."
            }) + "\n\n"
        return Response(error_stream(), mimetype="text/event-stream")

    tracker = PipelineContext()

    def event_stream():
        generator = run_optimization_pipeline(
            profile_path=PROFILE_PATH,
            jd_path=JD_PATH,
            main_tex_path=MAIN_TEX_PATH,
            generated_tex_path=GENERATED_TEX_PATH,
            output_dir=OUTPUT_DIR,
            tracker=tracker,
            is_cancelled=lambda: PIPELINE_CANCELLED,
            action=action
        )
        for update in generator:
            yield f"data: {json.dumps(update)}\n\n"

    return Response(event_stream(), mimetype="text/event-stream")

@app.route("/output/<filename>")
def serve_output(filename):
    """
    Serves output artifacts (resume.pdf, resume.png) to the browser.
    """
    # Prevent caching for live updates
    response = send_from_directory(OUTPUT_DIR, filename)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response

if __name__ == "__main__":
    # Start the local development server
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
