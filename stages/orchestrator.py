import os
import json
from utils.context import PipelineContext
from utils.helpers import extract_bullets
from stages.stage0_closeness_analyzer import run_stage0
from stages.stage1_text_generator import run_stage1
from stages.stage2_pdf_manager import run_stage2
from stages.stage3_vision_inspector import run_stage3

def run_optimization_pipeline(
    profile_path: str,
    jd_path: str,
    main_tex_path: str,
    generated_tex_path: str,
    output_dir: str,
    tracker: PipelineContext,
    is_cancelled=None,
    action: str = "all",
    selected_keywords: list = None,
    skipped_sections: list = None
):
    """
    Generator function that runs the 4-stage auto-correcting resume optimization loop.
    Yields dictionary updates for streaming progress logs to the Flask UI.
    """
    if is_cancelled and is_cancelled():
        yield {"status": "error", "message": "Pipeline cancelled by user.", "stage": 0}
        return

    gap_report_path = os.path.join(output_dir, "gap_report.json")
    gap_report = None

    # --- Stage 0: Semantic Gap Analyzer ---
    if action in ("all", "analyze"):
        yield {"status": "info", "message": "Initiating Stage 0: Semantic Gap Analyzer...", "stage": 0}
        yield {"status": "info", "message": "Stage 0: Sending user profile & job description to Gemini (waiting for LLM response)...", "stage": 0}
        try:
            gap_report = run_stage0(profile_path, jd_path, tracker)
            with open(gap_report_path, "w", encoding="utf-8") as f:
                json.dump(gap_report, f)
            yield {
                "status": "success",
                "message": f"Stage 0 Complete. Closeness Score: {gap_report.get('closeness_score')}%",
                "gap_report": gap_report,
                "stage": 0
            }
            if action == "analyze":
                yield {"status": "complete", "message": "Analysis phase complete.", "stage": 0, "gap_report": gap_report}
                return
        except Exception as e:
            yield {"status": "error", "message": f"Stage 0 Failed: {str(e)}", "stage": 0}
            return
    else:
        # action == "optimize"
        if os.path.exists(gap_report_path):
            try:
                with open(gap_report_path, "r", encoding="utf-8") as f:
                    gap_report = json.load(f)
            except Exception:
                gap_report = None
        
        if not gap_report:
            yield {"status": "info", "message": "No cached gap report found. Running Stage 0 analysis first...", "stage": 0}
            yield {"status": "info", "message": "Stage 0: Sending user profile & job description to Gemini (waiting for LLM response)...", "stage": 0}
            try:
                gap_report = run_stage0(profile_path, jd_path, tracker)
                with open(gap_report_path, "w", encoding="utf-8") as f:
                    json.dump(gap_report, f)
                yield {
                    "status": "success",
                    "message": f"Stage 0 Complete. Closeness Score: {gap_report.get('closeness_score')}%",
                    "gap_report": gap_report,
                    "stage": 0
                }
            except Exception as e:
                yield {"status": "error", "message": f"Stage 0 Failed: {str(e)}", "stage": 0}
                return

    if gap_report and selected_keywords is not None:
        gap_report["critical_gaps"] = selected_keywords
        gap_report["target_keywords"] = selected_keywords

    critique = ""
    png_path = os.path.join(output_dir, "resume.png")
    
    latex_content = None
    resume_json = None
    failing_bullets_to_optimize = None
    direction = "shorten"

    # --- Auto-Correcting Optimization Loop ---
    while not tracker.is_max_iterations_reached():
        if is_cancelled and is_cancelled():
            yield {"status": "error", "message": "Pipeline cancelled by user.", "stage": tracker.iteration}
            return
            
        iteration = tracker.increment_iteration()
        yield {
            "status": "info",
            "message": f"--- Starting Auto-Correcting Iteration {iteration} ---",
            "iteration": iteration
        }

        # Stage 1: Text Generation
        yield {"status": "info", "message": f"Stage 1: Generating tailored LaTeX content (Iteration {iteration})...", "stage": 1}
        yield {"status": "info", "message": f"Stage 1: Sending tailored prompt payload to Gemini (waiting for LLM response)...", "stage": 1}
        try:
            latex_content, resume_json = run_stage1(
                profile_path,
                jd_path,
                gap_report,
                critique,
                tracker,
                previous_json=resume_json if iteration > 1 else None,
                failing_bullets=failing_bullets_to_optimize,
                direction=direction,
                skipped_sections=skipped_sections
            )
            
            # Reset surgical parameters for this iteration's run
            failing_bullets_to_optimize = None
            direction = "shorten"

            # Prevent Plateau loops
            is_unique = tracker.register_content(latex_content)
            if not is_unique:
                yield {
                    "status": "warning",
                    "message": "Plateau loop detected: Generated content is identical to a prior iteration. Terminating loop to avoid resource waste.",
                    "stage": 1
                }
                break
        except Exception as e:
            yield {"status": "error", "message": f"Stage 1 Failed: {str(e)}", "stage": 1}
            return

        # Write generated data to disk
        try:
            with open(generated_tex_path, "w", encoding="utf-8") as f:
                f.write(latex_content)
        except Exception as e:
            yield {"status": "error", "message": f"Failed to write generated files: {str(e)}", "stage": 1}
            return

        # Stage 2: XeLaTeX Compiler & Page Boundary Validation
        yield {"status": "info", "message": "Stage 2: Compiling document with XeLaTeX & validating layout...", "stage": 2}
        yield {"status": "info", "message": "Stage 2: Running XeLaTeX compilation subprocess & generating PDF...", "stage": 2}
        success, compile_critique, overflowing_bullets = run_stage2(main_tex_path, output_dir)
        
        # Merge and write the clean final resume.tex to output_dir
        try:
            from utils.helpers import clean_and_write
            clean_and_write(main_tex_path, generated_tex_path, os.path.join(output_dir, "resume.tex"))
        except Exception as e:
            yield {"status": "warning", "message": f"Failed to write clean export resume.tex: {str(e)}", "stage": 2}

        if not success:
            critique = compile_critique
            if overflowing_bullets:
                failing_bullets_to_optimize = overflowing_bullets
            direction = "shorten"
            tracker.add_warning(f"Iteration {iteration}: Layout/Compile issue - {compile_critique}")
            yield {"status": "warning", "message": f"Stage 2 Layout Violation: {compile_critique}. Retrying...", "stage": 2}
            continue

        # Stage 3: Vision Inspection
        yield {"status": "info", "message": "Stage 3: Sending resume image to Vision model for layout review...", "stage": 3}
        yield {"status": "info", "message": "Stage 3: Sending rasterized layout image to Gemini Vision API (waiting for LLM response)...", "stage": 3}
        try:
            png_full_path = png_path.replace(".png", "_full.png")
            accepted, vision_critique = run_stage3(png_full_path, tracker)
            if not accepted:
                critique = vision_critique
                all_bullets = extract_bullets(latex_content)
                
                if "EMPTY_BOTTOM" in vision_critique:
                    all_bullets.sort(key=len)
                    failing_bullets_to_optimize = all_bullets[:3]
                    direction = "lengthen"
                else:
                    all_bullets.sort(key=len, reverse=True)
                    failing_bullets_to_optimize = all_bullets[:3]
                    direction = "shorten"

                tracker.add_warning(f"Iteration {iteration}: Vision Inspector Critique - {vision_critique}")
                yield {"status": "warning", "message": f"Stage 3 Visual Spacing Critique: {vision_critique}. Retrying...", "stage": 3}
                continue
            else:
                yield {
                    "status": "success",
                    "message": f"Stage 3 Complete. Resume Accepted! Spacing and margins are perfectly balanced.\nCritique details: {vision_critique}",
                    "stage": 3
                }
                break
        except Exception as e:
            yield {"status": "error", "message": f"Stage 3 Vision API call failed: {str(e)}", "stage": 3}
            return

    # Clean up resources/generated_data.tex in-place to remove debug helper macros
    try:
        from utils.helpers import clean_generated_file_in_place
        clean_generated_file_in_place(generated_tex_path)
    except Exception as e:
        tracker.add_warning(f"Failed to clean resources/generated_data.tex: {str(e)}")
    
    # Check if we exited loop due to max iterations
    from utils.config import MAX_ITERATIONS
    if tracker.iteration >= MAX_ITERATIONS and critique and not critique.startswith("STATUS: ACCEPTED"):
        yield {
            "status": "warning",
            "message": f"Auto-correcting pipeline reached the maximum of {MAX_ITERATIONS} iterations without full visual acceptance. Returning best-effort output.",
            "stage": 3
        }
    
    yield {
        "status": "complete",
        "message": "Resume compilation pipeline executed fully.",
        "telemetry": tracker.get_telemetry(),
        "warnings": tracker.warnings
    }
