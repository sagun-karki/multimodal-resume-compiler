import os
import json
from utils.context import PipelineContext
from utils.helpers import extract_bullets, extract_bullets_with_paths
from agents.ats_analyzer import ATSAnalyzerAgent
from agents.resume_writer import ResumeWriterAgent
from agents.visual_auditor import VisualAuditorAgent
from stages.stage2_pdf_manager import run_stage2

class CoordinatorAgent:
    def __init__(self, tracker: PipelineContext):
        self.tracker = tracker
        self.analyzer = ATSAnalyzerAgent(tracker)
        self.writer = ResumeWriterAgent(tracker)
        self.auditor = VisualAuditorAgent(tracker)

    def run_optimization(
        self,
        profile_path: str,
        jd_path: str,
        main_tex_path: str,
        generated_tex_path: str,
        output_dir: str,
        action: str = "all",
        selected_keywords: list = None,
        skipped_sections: list = None,
        is_cancelled=None
    ):
        """
        Runs the multi-agent optimization process. Coordinates between the
        ATS Analyzer, Resume Writer, Compiler tool, and Visual Auditor agents.
        Yields status dictionaries for real-time progress logging in the UI.
        """
        if is_cancelled and is_cancelled():
            yield {"status": "error", "event": "pipeline.cancelled", "message": "Pipeline cancelled by user.", "stage": 0}
            return

        gap_report_path = os.path.join(output_dir, "gap_report.json")
        gap_report = None

        # --- Phase 1: ATS Analyzer Agent (Gap Analysis) ---
        if action in ("all", "analyze"):
            yield {"status": "info", "event": "ats.start", "message": "[ATS Analyzer Agent] Comparing user profile against job description...", "stage": 0}
            try:
                with open(profile_path, "r", encoding="utf-8") as f:
                    profile_content = f.read()
                with open(jd_path, "r", encoding="utf-8") as f:
                    jd_content = f.read()

                gap_report = self.analyzer.analyze(profile_content, jd_content)
                with open(gap_report_path, "w", encoding="utf-8") as f:
                    json.dump(gap_report, f)

                yield {
                    "status": "success",
                    "message": f"[ATS Analyzer Agent] Gap analysis complete. Closeness Score: {gap_report.get('closeness_score')}%",
                    "gap_report": gap_report,
                    "stage": 0, "event": "ats.complete",
                    "telemetry": self.tracker.get_telemetry()
                }
                if action == "analyze":
                    yield {"status": "complete", "event": "analysis.complete", "message": "Analysis phase complete.", "stage": 0, "gap_report": gap_report, "telemetry": self.tracker.get_telemetry()}
                    return
            except Exception as e:
                yield {"status": "error", "message": f"[ATS Analyzer Agent] Failed: {str(e)}", "stage": 0}
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
                yield {"status": "info", "message": "No cached gap report found. Invoking [ATS Analyzer Agent]...", "stage": 0}
                try:
                    with open(profile_path, "r", encoding="utf-8") as f:
                        profile_content = f.read()
                    with open(jd_path, "r", encoding="utf-8") as f:
                        jd_content = f.read()

                    gap_report = self.analyzer.analyze(profile_content, jd_content)
                    with open(gap_report_path, "w", encoding="utf-8") as f:
                        json.dump(gap_report, f)

                    yield {
                        "status": "success",
                        "message": f"[ATS Analyzer Agent] Complete. Closeness Score: {gap_report.get('closeness_score')}%",
                        "gap_report": gap_report,
                        "stage": 0,
                        "telemetry": self.tracker.get_telemetry()
                    }
                except Exception as e:
                    yield {"status": "error", "message": f"[ATS Analyzer Agent] Failed: {str(e)}", "stage": 0}
                    return

        # Override gaps/keywords with UI selections if provided
        if gap_report and selected_keywords is not None:
            gap_report["critical_gaps"] = selected_keywords
            gap_report["target_keywords"] = selected_keywords

        critique = ""
        png_path = os.path.join(output_dir, "resume.png")
        
        latex_content = None
        resume_json = None
        failing_bullets_to_optimize = None
        direction = "shorten"

        # Read master profile once for the writer
        with open(profile_path, "r", encoding="utf-8") as f:
            profile_content = f.read()
        with open(jd_path, "r", encoding="utf-8") as f:
            jd_content = f.read()

        # --- Phase 2: Resume Writer & Visual Auditor Collaboration Loop ---
        while not self.tracker.is_max_iterations_reached():
            if is_cancelled and is_cancelled():
                yield {"status": "error", "message": "Pipeline cancelled by user.", "stage": self.tracker.iteration}
                return

            iteration = self.tracker.increment_iteration()
            yield {
                "status": "info",
                "message": f"--- Agent Collaboration Iteration {iteration} ---",
                "iteration": iteration
            }

            # Resume Writer Agent drafting/revising
            if failing_bullets_to_optimize:
                yield {
                    "status": "info",
                    "message": f"[Resume Writer Agent] Surgically rewriting {len(failing_bullets_to_optimize)} failing bullet points to {direction} them...",
                    "stage": 1
                }
            else:
                yield {
                    "status": "info",
                    "message": "[Resume Writer Agent] Drafting initial tailored resume JSON & LaTeX content...",
                    "stage": 1
                }

            try:
                latex_content, resume_json = self.writer.write_resume(
                    profile_content=profile_content,
                    jd_content=jd_content,
                    gap_report=gap_report,
                    critique=critique,
                    previous_json=resume_json if iteration > 1 else None,
                    failing_bullets=failing_bullets_to_optimize,
                    direction=direction,
                    skipped_sections=skipped_sections
                )
                
                # Reset search parameters for next loop iteration
                failing_bullets_to_optimize = None
                direction = "shorten"

                # Check for plateau loop
                is_unique = self.tracker.register_content(latex_content)
                if not is_unique:
                    yield {
                        "status": "warning",
                        "message": "[Resume Writer Agent] Plateau detected (content is identical to a prior draft). Stopping agent loop to prevent resource waste.",
                        "stage": 1
                    }
                    break
            except Exception as e:
                yield {"status": "error", "message": f"[Resume Writer Agent] Failed: {str(e)}", "stage": 1}
                return

            # Save draft LaTeX to file
            try:
                with open(generated_tex_path, "w", encoding="utf-8") as f:
                    f.write(latex_content)
            except Exception as e:
                yield {"status": "error", "message": f"Failed to save draft to file: {str(e)}", "stage": 1}
                return

            # Compile layout check tool
            yield {"status": "info", "message": "[Compiler Tool] Running LaTeX engine to compile draft...", "stage": 2}
            success, compile_critique, overflowing_bullets = run_stage2(main_tex_path, output_dir)

            # Export clean compiled source to output directory
            try:
                from utils.helpers import clean_and_write
                clean_and_write(main_tex_path, generated_tex_path, os.path.join(output_dir, "resume.tex"))
            except Exception as e:
                yield {"status": "warning", "message": f"[Compiler Tool] Warning writing export source: {str(e)}", "stage": 2}

            if not success:
                critique = compile_critique
                if overflowing_bullets:
                    failing_bullets_to_optimize = overflowing_bullets
                direction = "shorten"
                self.tracker.add_warning(f"Iteration {iteration}: Compile layout check failure - {compile_critique}")
                yield {"status": "warning", "message": f"[Compiler Tool] Layout Overflow check failed: {compile_critique}. Instructing Writer Agent to compression.", "stage": 2}
                continue

            # Visual Audit Agent review
            yield {"status": "info", "message": "[Visual Auditor Agent] Reviewing rendered layout design & spacing...", "stage": 3}
            try:
                png_full_path = png_path.replace(".png", "_full.png")
                accepted, vision_critique = self.auditor.audit(png_full_path)
                
                if not accepted:
                    critique = vision_critique
                    pairs = extract_bullets_with_paths(latex_content)
                    
                    if "EMPTY_BOTTOM" in vision_critique:
                        # Sort by bullet text length ascending (shortest first)
                        pairs.sort(key=lambda p: len(p[1]))
                        failing_bullets_to_optimize = [p[0] for p in pairs[:3] if p[0]]
                        direction = "lengthen"
                    else:
                        # Sort by bullet text length descending (longest first)
                        pairs.sort(key=lambda p: len(p[1]), reverse=True)
                        failing_bullets_to_optimize = [p[0] for p in pairs[:3] if p[0]]
                        direction = "shorten"

                    self.tracker.add_warning(f"Iteration {iteration}: Visual Auditor Critique - {vision_critique}")
                    yield {"status": "warning", "message": f"[Visual Auditor Agent] Critique: {vision_critique}. Requesting Writer Agent revisions.", "stage": 3}
                    continue
                else:
                    yield {
                        "status": "success",
                        "message": f"[Visual Auditor Agent] Accepted! Layout is perfectly balanced. Critique details: {vision_critique}",
                        "stage": 3
                    }
                    break
            except Exception as e:
                yield {"status": "error", "message": f"[Visual Auditor Agent] Failed: {str(e)}", "stage": 3}
                return

        # Post-process clean-up of temporary files
        try:
            from utils.helpers import clean_generated_file_in_place
            clean_generated_file_in_place(generated_tex_path)
        except Exception as e:
            self.tracker.add_warning(f"Failed to clean resources/generated_data.tex: {str(e)}")

        from utils.config import MAX_ITERATIONS
        if self.tracker.iteration >= MAX_ITERATIONS and critique and not critique.startswith("STATUS: ACCEPTED"):
            yield {
                "status": "warning",
                "message": f"Agent collaboration loop reached limit of {MAX_ITERATIONS} iterations without full visual consensus. Returning best draft.",
                "stage": 3
            }

        yield {
            "status": "complete",
            "message": "Resume multi-agent collaboration loop finished fully.",
            "telemetry": self.tracker.get_telemetry(),
            "warnings": self.tracker.warnings
        }
