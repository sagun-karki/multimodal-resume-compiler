import os
import json
import uuid
import logging
from threading import Event
from flask import Flask, render_template, request, jsonify, Response, send_from_directory
from dotenv import load_dotenv

load_dotenv()

from utils.context import PipelineContext
from stages.orchestrator import run_optimization_pipeline

app = Flask(__name__)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

WORKSPACE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(WORKSPACE, "my-content")
RESOURCES_DIR = os.path.join(WORKSPACE, "resources")
OUTPUT_DIR = os.path.join(WORKSPACE, "output")

PROFILE_PATH = os.path.join(CONTENT_DIR, "user_profile.md")
JD_PATH = os.path.join(CONTENT_DIR, "job_description.txt")
MAIN_TEX_PATH = os.path.join(RESOURCES_DIR, "resume.tex")
GENERATED_TEX_PATH = os.path.join(RESOURCES_DIR, "generated_data.tex")

os.makedirs(CONTENT_DIR, exist_ok=True)
os.makedirs(RESOURCES_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

_CANCEL_TOKENS: dict[str, Event] = {}


def _get_or_create_cancel_token(run_id: str) -> Event:
    token = _CANCEL_TOKENS.get(run_id)
    if token is None:
        token = Event()
        _CANCEL_TOKENS[run_id] = token
    return token


@app.route("/")
def index():
    pdf_path = os.path.join(OUTPUT_DIR, "resume.pdf")
    png_path = os.path.join(OUTPUT_DIR, "resume.png")
    if not os.path.exists(pdf_path) or not os.path.exists(png_path):
        try:
            from stages.stage2_pdf_manager import run_stage2
            from utils.helpers import clean_and_write
            logger.info("Default resume outputs missing. Compiling...")
            run_stage2(MAIN_TEX_PATH, OUTPUT_DIR)
            clean_and_write(MAIN_TEX_PATH, GENERATED_TEX_PATH, os.path.join(OUTPUT_DIR, "resume.tex"))
        except Exception as e:
            logger.error("Failed to compile default resume files on startup/load: %s", str(e))

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
    data = request.json or {}
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


@app.route("/api/cancel", methods=["POST"])
def cancel_pipeline():
    data = request.json or {}
    run_id = data.get("run_id", "default")
    _get_or_create_cancel_token(run_id).set()
    return jsonify({"status": "success", "message": "Cancellation request received.", "run_id": run_id})


@app.route("/api/compile-default", methods=["POST"])
def compile_default():
    from stages.stage2_pdf_manager import run_stage2

    success, err, _ = run_stage2(MAIN_TEX_PATH, OUTPUT_DIR)
    if success:
        return jsonify({"status": "success", "message": "Default resume compilation successful."})
    return jsonify({"status": "error", "message": err}), 500


@app.route("/stream")
def compile_stream():
    action = request.args.get("action", "all")
    run_id = request.args.get("run_id") or str(uuid.uuid4())

    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        def error_stream():
            yield "data: " + json.dumps({
                "status": "error",
                "message": "API_KEY_ERROR: GEMINI_API_KEY or GOOGLE_API_KEY environment variable is not set."
            }) + "\n\n"
        return Response(error_stream(), mimetype="text/event-stream")

    tracker = PipelineContext()
    cancel_token = _get_or_create_cancel_token(run_id)
    cancel_token.clear()

    def _safe_json_param(name):
        raw = request.args.get(name)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            logger.warning("Invalid JSON for param '%s'", name)
            return None

    selected_keywords = _safe_json_param("keywords")
    skipped_sections = _safe_json_param("skipped_sections")

    def event_stream():
        logger.info("pipeline.start run_id=%s action=%s", run_id, action)
        try:
            generator = run_optimization_pipeline(
                profile_path=PROFILE_PATH,
                jd_path=JD_PATH,
                main_tex_path=MAIN_TEX_PATH,
                generated_tex_path=GENERATED_TEX_PATH,
                output_dir=OUTPUT_DIR,
                tracker=tracker,
                is_cancelled=cancel_token.is_set,
                action=action,
                selected_keywords=selected_keywords,
                skipped_sections=skipped_sections,
            )
            for update in generator:
                if isinstance(update, dict):
                    update.setdefault("run_id", run_id)
                yield f"data: {json.dumps(update)}\n\n"
        finally:
            _CANCEL_TOKENS.pop(run_id, None)
            logger.info("pipeline.end run_id=%s", run_id)

    return Response(event_stream(), mimetype="text/event-stream")


@app.route("/output/<filename>")
def serve_output(filename):
    response = send_from_directory(OUTPUT_DIR, filename)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
