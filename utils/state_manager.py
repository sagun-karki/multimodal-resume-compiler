import hashlib
from typing import List, Set
from utils.config import MAX_ITERATIONS

class StateManager:
    def __init__(self):
        self.iteration = 0
        self.history_hashes: List[str] = []
        self.warnings: List[str] = []

    def increment_iteration(self) -> int:
        self.iteration += 1
        return self.iteration

    def is_max_iterations_reached(self) -> bool:
        return self.iteration >= MAX_ITERATIONS

    def compute_hash(self, content: str) -> str:
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def register_content(self, content: str) -> bool:
        """
        Calculates content hash. Returns True if hash is unique (new), 
        or False if it matches a previously generated round (indicating a plateau loop).
        """
        content_hash = self.compute_hash(content)
        if content_hash in self.history_hashes:
            return False
        self.history_hashes.append(content_hash)
        return True

    def add_warning(self, warning: str):
        self.warnings.append(warning)

    def clear(self):
        self.iteration = 0
        self.history_hashes = []
        self.warnings = []
