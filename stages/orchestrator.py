import os
import json
from utils.state_manager import StateManager
from utils.token_tracker import TokenTracker
from utils.helpers import extract_bullets
from stages.stage0_closeness_analyzer import run_stage0
from stages.stage1_text_generator import run_stage1
from stages.stage2_python_sanitizer import run_stage2
from stages.stage3_latex_compiler import run_stage3
from stages.stage4_pymupdf_router import run_stage4
from stages.stage5_vision_inspector import run_stage5

def run_optimization_pipeline(
    profile_path: str,
    jd_path: str,
    main_tex_path: str,
    generated_tex_path: str,
    output_dir: str,
    tracker: TokenTracker,
    is_cancelled=None,
    action: str = "all"
):
    """
    Generator function that runs the 6-stage auto-correcting resume optimization loop.
    Yields dictionary updates for streaming progress logs to the Flask UI.
    """
    state = StateManager()
    
    if is_cancelled and is_cancelled():
        yield {"status": "error", "message": "Pipeline cancelled by user.", "stage": 0}
        return

    gap_report_path = os.path.join(output_dir, "gap_report.json")
    gap_report = None

    if action in ("all", "analyze"):
        yield {"status": "info", "message": "Initiating Stage 0: Semantic Gap Analyzer...", "stage": 0}
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

    critique = ""
    pdf_path = os.path.join(output_dir, "resume.pdf")
    png_path = os.path.join(output_dir, "resume.png")
    
    latex_content = None
    resume_json = None
    failing_bullets_to_optimize = None
    direction = "shorten"

    while not state.is_max_iterations_reached():
        if is_cancelled and is_cancelled():
            yield {"status": "error", "message": "Pipeline cancelled by user.", "stage": state.iteration}
            return
        iteration = state.increment_iteration()
        yield {
            "status": "info",
            "message": f"--- Starting Auto-Correcting Iteration {iteration}/{state.iteration if state.iteration else 5} ---",
            "iteration": iteration
        }

        # Stage 1: Text Generation
        yield {"status": "info", "message": f"Stage 1: Generating tailored LaTeX content (Iteration {iteration})...", "stage": 1}
        try:
            latex_content, resume_json = run_stage1(
                profile_path,
                jd_path,
                gap_report,
                critique,
                tracker,
                previous_json=resume_json if iteration > 1 else None,
                failing_bullets=failing_bullets_to_optimize,
                direction=direction
            )
            
            # Reset surgical parameters for this iteration's run
            failing_bullets_to_optimize = None
            direction = "shorten"

            # Prevent Plateau loops
            is_unique = state.register_content(latex_content)
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

        # Stage 2: Programmatic Sanitizer
        yield {"status": "info", "message": "Stage 2: Running programmatic LaTeX sanitizer & orphan detector...", "stage": 2}
        sanitized_content, success, sanitize_err, failing_bullets = run_stage2(latex_content)
        
        # Use sanitized content as the base
        latex_content = sanitized_content

        if not success:
            critique = sanitize_err
            failing_bullets_to_optimize = failing_bullets
            direction = "shorten"
            state.add_warning(f"Iteration {iteration}: Sanitizer Error - {sanitize_err}")
            yield {"status": "warning", "message": f"Stage 2 Alert: {sanitize_err}. Retrying...", "stage": 2}
            continue

        # Write sanitized data to disk
        try:
            with open(generated_tex_path, "w", encoding="utf-8") as f:
                f.write(sanitized_content)
            
            # Merge and write the clean final resume.tex to output_dir
            from utils.latex_cleaner import clean_and_write
            clean_and_write(main_tex_path, generated_tex_path, os.path.join(output_dir, "resume.tex"))
        except Exception as e:
            yield {"status": "error", "message": f"Failed to write generated files: {str(e)}", "stage": 2}
            return

        # Stage 3: XeLaTeX Compiler
        yield {"status": "info", "message": "Stage 3: Compiling document with XeLaTeX...", "stage": 3}
        success, compile_critique, overflowing_bullets = run_stage3(main_tex_path, output_dir)
        
        # Always rasterize the PNG so the UI can show the current state, even if compilation had typographic errors
        router_success, router_critique = True, ""
        try:
            from stages.stage4_pymupdf_router import run_stage4
            router_success, router_critique = run_stage4(pdf_path, png_path)
        except Exception as e:
            yield {"status": "warning", "message": f"Failed to rasterize PNG: {str(e)}", "stage": 4}

        if not success:
            critique = compile_critique
            if overflowing_bullets:
                failing_bullets_to_optimize = overflowing_bullets
            direction = "shorten"
            state.add_warning(f"Iteration {iteration}: Compiler Critique - {compile_critique}")
            yield {"status": "warning", "message": f"Stage 3 Compile Issue: {compile_critique}. Retrying...", "stage": 3}
            continue

        # Stage 4: Page Count Router validation
        yield {"status": "info", "message": "Stage 4: Checking page boundaries...", "stage": 4}
        if not router_success:
            critique = router_critique
            all_bullets = extract_bullets(latex_content)
            all_bullets.sort(key=len, reverse=True)
            failing_bullets_to_optimize = all_bullets[:3]
            direction = "shorten"
            state.add_warning(f"Iteration {iteration}: Page Router Issue - {router_critique}")
            yield {"status": "warning", "message": f"Stage 4 Layout Violation: {router_critique}. Retrying...", "stage": 4}
            continue

        # Stage 5: Vision Inspection
        yield {"status": "info", "message": "Stage 5: Sending resume image to Vision model for layout review...", "stage": 5}
        try:
            accepted, vision_critique = run_stage5(png_path, tracker)
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

                state.add_warning(f"Iteration {iteration}: Vision Inspector Critique - {vision_critique}")
                yield {"status": "warning", "message": f"Stage 5 Visual Spacing Critique: {vision_critique}. Retrying...", "stage": 5}
                continue
            else:
                yield {
                    "status": "success",
                    "message": f"Stage 5 Complete. Resume Accepted! Spacing and margins are perfectly balanced.\nCritique details: {vision_critique}",
                    "stage": 5
                }
                break
        except Exception as e:
            yield {"status": "error", "message": f"Stage 5 Vision API call failed: {str(e)}", "stage": 5}
            return

    # Clean up resources/generated_data.tex in-place to remove any \validatedbullet commands for clean source access
    try:
        from utils.latex_cleaner import clean_generated_file_in_place
        clean_generated_file_in_place(generated_tex_path)
    except Exception as e:
        state.add_warning(f"Failed to clean resources/generated_data.tex: {str(e)}")

    # Check if we exited loop due to max iterations
    from utils.config import MAX_ITERATIONS
    if state.iteration >= MAX_ITERATIONS and critique and not critique.startswith("STATUS: ACCEPTED"):
        yield {
            "status": "warning",
            "message": f"Auto-correcting pipeline reached the maximum of {MAX_ITERATIONS} iterations without full visual acceptance. Returning best-effort output.",
            "stage": 5
        }
    
    yield {
        "status": "complete",
        "message": "Resume compilation pipeline executed fully.",
        "telemetry": tracker.get_telemetry(),
        "warnings": state.warnings
    }
