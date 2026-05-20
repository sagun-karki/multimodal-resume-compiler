import hashlib
import threading
from typing import List
from utils.config import PRICING, MAX_ITERATIONS

class PipelineContext:
    def __init__(self):
        self._lock = threading.Lock()
        
        # Token and cost tracking
        self.input_tokens = 0
        self.output_tokens = 0
        self.accumulated_cost = 0.0
        
        # Iteration and loop state
        self.iteration = 0
        self.history_hashes: List[str] = []
        self.warnings: List[str] = []

    def track(self, model_type: str, input_tokens: int, output_tokens: int) -> float:
        """Track input/output tokens and update total accumulated cost."""
        with self._lock:
            self.input_tokens += input_tokens
            self.output_tokens += output_tokens
            
            in_rate = PRICING.get(model_type, {}).get("input", 0.0) / 1_000_000
            out_rate = PRICING.get(model_type, {}).get("output", 0.0) / 1_000_000
            
            cost = (input_tokens * in_rate) + (output_tokens * out_rate)
            self.accumulated_cost += cost
            return cost

    def get_telemetry(self) -> dict:
        """Get current token and cost statistics."""
        with self._lock:
            return {
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "accumulated_cost": round(self.accumulated_cost, 6)
            }

    def increment_iteration(self) -> int:
        """Increment current loop iteration index and return it."""
        with self._lock:
            self.iteration += 1
            return self.iteration

    def is_max_iterations_reached(self) -> bool:
        """Check if pipeline has reached the maximum allowed iterations constraint."""
        with self._lock:
            return self.iteration >= MAX_ITERATIONS

    def register_content(self, content: str) -> bool:
        """
        Calculates content hash. Returns True if hash is unique (new), 
        or False if it matches a previously generated round (indicating a plateau loop).
        """
        content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
        with self._lock:
            if content_hash in self.history_hashes:
                return False
            self.history_hashes.append(content_hash)
            return True

    def add_warning(self, warning: str):
        """Append a warning message to the execution context log."""
        with self._lock:
            self.warnings.append(warning)

    def reset(self):
        """Reset state, token count, and telemetry tracking."""
        with self._lock:
            self.input_tokens = 0
            self.output_tokens = 0
            self.accumulated_cost = 0.0
            self.iteration = 0
            self.history_hashes = []
            self.warnings = []
