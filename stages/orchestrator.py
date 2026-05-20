import os
import json
from utils.context import PipelineContext
from agents.coordinator import CoordinatorAgent

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
    Orchestration entry point. Instantiates and delegates execution to the
    multi-agent CoordinatorAgent supervisor.
    """
    coordinator = CoordinatorAgent(tracker)
    yield from coordinator.run_optimization(
        profile_path=profile_path,
        jd_path=jd_path,
        main_tex_path=main_tex_path,
        generated_tex_path=generated_tex_path,
        output_dir=output_dir,
        action=action,
        selected_keywords=selected_keywords,
        skipped_sections=skipped_sections,
        is_cancelled=is_cancelled
    )
