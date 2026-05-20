import os

TEXT_MODEL = os.getenv("TEXT_MODEL", "gemini-2.5-flash")
VISION_MODEL = os.getenv("VISION_MODEL", "gemini-2.5-flash")

PRICING = {
    "text": {"input": 0.075, "output": 0.30},
    "vision": {"input": 0.075, "output": 0.30},
}

MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "2"))
LATEX_TIMEOUT_SECONDS = int(os.getenv("LATEX_TIMEOUT_SECONDS", "30"))

RISKY_LENGTH_MIN = 90
RISKY_LENGTH_MAX = 112
TARGET_PAGE_LIMIT = 1
