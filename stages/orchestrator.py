import os
import json
from utils.state_manager import StateManager
from utils.token_tracker import TokenTracker
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
    tracker: TokenTracker
):
    """
    Generator function that runs the 6-stage self-healing resume optimization loop.
    Yields dictionary updates for streaming progress logs to the Flask UI.
    """
    state = StateManager()
    
    yield {"status": "info", "message": "Initiating Stage 0: Semantic Gap Analyzer...", "stage": 0}
    try:
        gap_report = run_stage0(profile_path, jd_path, tracker)
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
    failing_bullets_to_optimize = None
    direction = "shorten"

    while not state.is_max_iterations_reached():
        iteration = state.increment_iteration()
        yield {
            "status": "info",
            "message": f"--- Starting Self-Healing Iteration {iteration}/{state.iteration if state.iteration else 5} ---",
            "iteration": iteration
        }

        # Stage 1: Text Generation
        yield {"status": "info", "message": f"Stage 1: Generating tailored LaTeX content (Iteration {iteration})...", "stage": 1}
        try:
            latex_content = run_stage1(
                profile_path,
                jd_path,
                gap_report,
                critique,
                tracker,
                previous_latex=latex_content if iteration > 1 else None,
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
        except Exception as e:
            yield {"status": "error", "message": f"Failed to write generated_data.tex: {str(e)}", "stage": 2}
            return

        # Stage 3: XeLaTeX Compiler
        yield {"status": "info", "message": "Stage 3: Compiling document with XeLaTeX...", "stage": 3}
        success, compile_critique, overflowing_bullets = run_stage3(main_tex_path, output_dir)
        if not success:
            critique = compile_critique
            if overflowing_bullets:
                failing_bullets_to_optimize = overflowing_bullets
            direction = "shorten"
            state.add_warning(f"Iteration {iteration}: Compiler Critique - {compile_critique}")
            yield {"status": "warning", "message": f"Stage 3 Compile Issue: {compile_critique}. Retrying...", "stage": 3}
            continue

        # Stage 4: Page Count Router & Rasterizer
        yield {"status": "info", "message": "Stage 4: Checking page boundaries and rasterizing to PNG...", "stage": 4}
        success, router_critique = run_stage4(pdf_path, png_path)
        if not success:
            critique = router_critique
            from stages.stage1_text_generator import extract_bullets
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
                from stages.stage1_text_generator import extract_bullets
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

    # Check if we exited loop due to max iterations
    if state.iteration >= 5 and critique and not critique.startswith("STATUS: ACCEPTED"):
        yield {
            "status": "warning",
            "message": "Self-healing pipeline reached the maximum of 5 iterations without full visual acceptance. Returning best-effort output.",
            "stage": 5
        }
    
    yield {
        "status": "complete",
        "message": "Resume compilation pipeline executed fully.",
        "telemetry": tracker.get_telemetry(),
        "warnings": state.warnings
    }
