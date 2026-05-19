# Configuration variables for the optimization engine

# Models configuration
TEXT_MODEL = "gemini-2.5-flash"
VISION_MODEL = "gemini-2.5-flash"

# API Pricing Coefficients (per 1 Million tokens)
PRICING = {
    "text": {
        "input": 0.075,
        "output": 0.30
    },
    "vision": {
        "input": 0.075,
        "output": 0.30
    }
}

# Execution Constraints
MAX_ITERATIONS = 1

# Typography and Layout boundaries
RISKY_LENGTH_MIN = 90
RISKY_LENGTH_MAX = 112
TARGET_PAGE_LIMIT = 1
