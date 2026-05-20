import google.generativeai as genai
from utils.helpers import get_api_key, track_tokens
from utils.context import PipelineContext

class BaseAgent:
    def __init__(self, name: str, system_instruction: str, model_name: str, tracker: PipelineContext):
        self.name = name
        self.system_instruction = system_instruction
        self.model_name = model_name
        self.tracker = tracker
        
        api_key = get_api_key()
        genai.configure(api_key=api_key)
        
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=self.system_instruction
        )
        
    def generate_response(self, contents, generation_config: dict = None, model_type: str = "text") -> str:
        """Call Gemini API and track tokens."""
        if generation_config is None:
            generation_config = {"temperature": 0.2}
            
        response = self.model.generate_content(
            contents,
            generation_config=generation_config
        )
        
        track_tokens(response, self.tracker, model_type=model_type)
        return response.text.strip()
