import os
import json
import typing
import abc
from fastapi import HTTPException, status
from google import genai
from google.genai import types
import openai
import anthropic
from ..config import settings

# Abstract Base Class for AI Providers
class AIProvider(abc.ABC):
    @abc.abstractmethod
    async def extract_data(self, image_bytes: bytes, mime_type: str) -> dict:
        pass

# Gemini Provider (Updated for google-genai SDK)
class GeminiProvider(AIProvider):
    def __init__(self):
        if not settings.GOOGLE_API_KEY:
             raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not set")
        
        # Initialize the client with the API key
        self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    async def extract_data(self, image_bytes: bytes, mime_type: str) -> dict:
        try:
            prompt = self._get_prompt()
            
            # Use the async client (aio)
            response = await self.client.aio.models.generate_content(
                model="gemini-2.0-flash-001",
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=prompt),
                            types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
                        ]
                    )
                ],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )
            return json.loads(response.text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gemini Error: {str(e)}")

    def _get_prompt(self):
        return """
        Extract the following fields from the handwritten form image and return as JSON:
        {
            "name": "string or null",
            "gender": "string or null",
            "email": "string or null",
            "phone_number": "string or null",
            "date_of_birth": "string or null",
            "relationship_status": "string or null",
            "country": "string or null",
            "state": "string or null",
            "address": "string or null",
            "nearest_bus_stop": "string or null",
            "is_student": boolean (default false),
            "age_group": "string or null",
            "school": "string or null",
            "occupation": "string or null",
            "denomination": "string or null",
            "availability_for_follow_up": boolean (default true),
            "online": boolean (default false)
        }
        """

# OpenAI Provider (GPT-4o)
class OpenAIProvider(AIProvider):
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise HTTPException(status_code=500, detail="OPENAI_API_KEY not set")
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def extract_data(self, image_bytes: bytes, mime_type: str) -> dict:
        import base64
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self._get_prompt()},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"OpenAI Error: {str(e)}")

    def _get_prompt(self):
        return """
        Extract data from this form image. Return ONLY a valid JSON object with these keys:
        name, gender, email, phone_number, date_of_birth, relationship_status, country, state, address, 
        nearest_bus_stop, is_student (bool), age_group, school, occupation, denomination, 
        availability_for_follow_up (bool), online (bool).
        Use null for missing fields.
        """

# Claude Provider (Claude 3.5 Sonnet)
class ClaudeProvider(AIProvider):
    def __init__(self):
        if not settings.ANTHROPIC_API_KEY:
            raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not set")
        self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def extract_data(self, image_bytes: bytes, mime_type: str) -> dict:
        import base64
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        try:
            message = await self.client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=4096,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": base64_image
                                }
                            },
                            {
                                "type": "text",
                                "text": self._get_prompt()
                            }
                        ]
                    }
                ]
            )
            # Claude returns text, we need to parse JSON from it. 
            # Usually it's good at following instructions to return only JSON.
            response_text = message.content[0].text
            # Basic cleanup in case of markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                 response_text = response_text.split("```")[1].split("```")[0]
                 
            return json.loads(response_text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Claude Error: {str(e)}")

    def _get_prompt(self):
        return """
        Extract data from this form image. Return ONLY a valid JSON object. 
        Do not include any conversational text.
        Keys: name, gender, email, phone_number, date_of_birth, relationship_status, country, state, address, 
        nearest_bus_stop, is_student (bool), age_group, school, occupation, denomination, 
        availability_for_follow_up (bool), online (bool).
        """

# Factory
def get_ai_provider() -> AIProvider:
    provider = settings.AI_MODEL_PROVIDER.lower()
    if provider == "openai":
        return OpenAIProvider()
    elif provider == "anthropic":
        return ClaudeProvider()
    else:
        return GeminiProvider()

# Public API
async def process_batch(files: list) -> typing.List[dict]:
    provider = get_ai_provider()
    results = []
    
    for file in files:
        try:
            content = await file.read()
            # Basic MIME type fix/check
            mime_type = file.content_type or "image/jpeg" 
            
            data = await provider.extract_data(content, mime_type)
            
            # Post-processing to ensure defaults
            # Handle cases where AI returns explicit null/None
            if data.get("is_student") is None:
                data["is_student"] = False
            if data.get("availability_for_follow_up") is None:
                data["availability_for_follow_up"] = True
            if data.get("online") is None:
                data["online"] = False
            
            results.append(data)
        except Exception as e:
            print(f"Error processing {file.filename}: {e}")
            # Optionally return an error object or None
            results.append({"error": str(e), "file": file.filename})
            
    return results
