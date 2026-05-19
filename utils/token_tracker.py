import threading
from utils.config import PRICING

class TokenTracker:
    def __init__(self):
        self._lock = threading.Lock()
        self.input_tokens = 0
        self.output_tokens = 0
        self.accumulated_cost = 0.0

    def track(self, model_type: str, input_tokens: int, output_tokens: int):
        """
        model_type: 'text' or 'vision'
        """
        with self._lock:
            self.input_tokens += input_tokens
            self.output_tokens += output_tokens
            
            # Cost per 1M tokens
            in_rate = PRICING.get(model_type, {}).get("input", 0.0) / 1_000_000
            out_rate = PRICING.get(model_type, {}).get("output", 0.0) / 1_000_000
            
            cost = (input_tokens * in_rate) + (output_tokens * out_rate)
            self.accumulated_cost += cost
            return cost

    def get_telemetry(self):
        with self._lock:
            return {
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "accumulated_cost": round(self.accumulated_cost, 6)
            }

    def reset(self):
        with self._lock:
            self.input_tokens = 0
            self.output_tokens = 0
            self.accumulated_cost = 0.0
