# Configuration variables for the optimization engine

# Models configuration
TEXT_MODEL = "gpt-4o-mini"
VISION_MODEL = "gpt-4o"

# API Pricing Coefficients (per 1 Million tokens)
PRICING = {
    "text": {
        "input": 0.15,
        "output": 0.60
    },
    "vision": {
        "input": 2.50,
        "output": 10.00
    }
}

# Execution Constraints
MAX_ITERATIONS = 5

# Typography and Layout boundaries
RISKY_LENGTH_MIN = 90
RISKY_LENGTH_MAX = 112
TARGET_PAGE_LIMIT = 1
