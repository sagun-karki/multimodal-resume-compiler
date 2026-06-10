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
        self.history_embeddings: List[List[float]] = []
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
        Calculates content hash and embedding. Returns True if unique (new), 
        or False if it matches or is semantically too close to a previous round (plateau).
        """
        import hashlib
        import math
        content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
        
        with self._lock:
            if content_hash in self.history_hashes:
                return False
            self.history_hashes.append(content_hash)
            
            # Semantic similarity check with previous iteration
            from utils.helpers import get_api_key
            import google.generativeai as genai
            
            try:
                api_key = get_api_key()
                genai.configure(api_key=api_key)
                res = genai.embed_content(
                    model="models/text-embedding-004",
                    content=content,
                    task_type="semantic_similarity"
                )
                new_embedding = res.get("embedding")
            except Exception as e:
                self.warnings.append(f"Failed to fetch content embedding: {e}")
                new_embedding = None
                
            if new_embedding and self.history_embeddings:
                prev_embedding = self.history_embeddings[-1]
                dot_product = sum(x * y for x, y in zip(new_embedding, prev_embedding))
                norm_new = math.sqrt(sum(x * x for x in new_embedding))
                norm_prev = math.sqrt(sum(x * x for x in prev_embedding))
                
                if norm_new > 0 and norm_prev > 0:
                    similarity = dot_product / (norm_new * norm_prev)
                    if similarity > 0.98:
                        self.warnings.append(f"Semantic similarity plateau detected: {similarity:.4f} > 0.98")
                        return False
            
            if new_embedding:
                self.history_embeddings.append(new_embedding)
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
            self.history_embeddings = []
            self.warnings = []
