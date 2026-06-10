# How to Update the LaTeX Resume Template

To update the resume template layout yourself using an external Large Language Model (LLM) of your choice, follow these instructions to extract the necessary structural code, package your request for the AI, and integrate the modifications back into the repository.

### Step 1: Collect the Template Files

To alter the visual architecture, font geometry, or data schema, you need to provide the external LLM with the files that govern layout and structure. Grab these files from your project directory:

1. **`resources/resume.tex`**: This contains the global LaTeX layout configurations, including margins, package imports, font classifications, and section line dividers.
2. **`templates/body.tex.j2`**: This is the Jinja2 LaTeX template loop structure that dictates how your profile sections and item bullets are ordered and structurally rendered.
3. **`agents/resume_writer.py`**: This file contains the structured Pydantic input schemas (`FullResumeSchema`, `JobExperience`, `Project`, etc.). If you plan to add new data fields (such as a GPA or a project URL), the external AI must modify these schemas so the pipeline generates matching JSON objects.

### Step 2: Use an AI of Your Choice to Generate Updates

Provide the code from the three files above to an external LLM (e.g., Gemini, ChatGPT, Claude) along with your desired template style instructions. You can use the following prompt template for the AI:

```text
I am using an autonomous multimodal resume compiler pipeline. I want to change my resume template layout.

Here are my project files:
--- FILE 1: resources/resume.tex ---
[Paste content of resources/resume.tex]

--- FILE 2: templates/body.tex.j2 ---
[Paste content of templates/body.tex.j2]

--- FILE 3: agents/resume_writer.py (Focus on Pydantic Schemas) ---
[Paste the Pydantic classes section from agents/resume_writer.py]

MY GOAL:
[Insert your target design changes here. Examples:
 - "Change the template font setup to a modern Sans-Serif stack and compress vertical section spacing."
 - "Add a new 'gpa' field to the Education block and a 'portfolio_url' field to the Contact section, updating both the LaTeX formatting and the Python Pydantic structured schemas synchronously."]

CRITICAL CONSTRAINT:
Do not include any hardcoded personal data inside 'templates/body.tex.j2'. Keep the data rendering dynamic using the Jinja2 variables (e.g., {{ job.title }}).

Please provide the updated code for all three files.
```

### Step 3: Apply the AI Output Back to Your Project

Once the external LLM provides the revised code, update the files in your project workspace:

1. Open **`resources/resume.tex`** and overwrite it with the AI's updated LaTeX configuration.
2. Open **`templates/body.tex.j2`** and overwrite it with the new structural loop layouts.
3. Update the Pydantic definitions inside **`agents/resume_writer.py`** and ensure you mirror those identical schema changes inside **`stages/stage1_text_generator.py`** to avoid structured output mismatches.

### Step 4: Validate and Compile

After modifying the source template files, run a clean compilation check to test the formatting structure before starting a full optimization pipeline run:

```bash
make clean
make compile
```

The multi-agent orchestration loop will automatically adapt to your new static design template, programmatically trimming or lengthening text density in subsequent runs to fit your updated layout baseline.
