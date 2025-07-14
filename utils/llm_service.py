"""
Project Chimera - LLM Service
Unified interface for interacting with different LLM providers (OpenAI, Anthropic)
"""

import os
import json
import asyncio
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import logging

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

@dataclass
class LLMResponse:
    """Standardized response from LLM providers"""
    content: str
    provider: str
    model: str
    tokens_used: Optional[int] = None
    cost_estimate: Optional[float] = None
    error: Optional[str] = None

class LLMService:
    """Unified LLM service supporting multiple providers"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.default_provider = os.getenv("DEFAULT_LLM_PROVIDER", "openai")
        
        # Initialize clients
        self.openai_client = None
        self.anthropic_client = None
        
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize LLM clients based on available API keys"""
        
        # OpenAI
        if OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
            try:
                self.openai_client = openai.OpenAI(
                    api_key=os.getenv("OPENAI_API_KEY")
                )
                self.logger.info("OpenAI client initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize OpenAI client: {e}")
        
        # Anthropic
        if ANTHROPIC_AVAILABLE and os.getenv("ANTHROPIC_API_KEY"):
            try:
                self.anthropic_client = anthropic.Anthropic(
                    api_key=os.getenv("ANTHROPIC_API_KEY")
                )
                self.logger.info("Anthropic client initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize Anthropic client: {e}")
    
    async def generate_response(
        self, 
        prompt: str, 
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None
    ) -> LLMResponse:
        """Generate response using specified or default LLM provider"""
        
        provider = provider or self.default_provider
        
        try:
            if provider == "openai" and self.openai_client:
                return await self._generate_openai_response(
                    prompt, model, max_tokens, temperature, system_prompt
                )
            elif provider == "anthropic" and self.anthropic_client:
                return await self._generate_anthropic_response(
                    prompt, model, max_tokens, temperature, system_prompt
                )
            else:
                error_msg = f"Provider '{provider}' not available or not configured"
                self.logger.error(error_msg)
                return LLMResponse(
                    content="",
                    provider=provider,
                    model="unknown",
                    error=error_msg
                )
        
        except Exception as e:
            error_msg = f"Error generating response with {provider}: {str(e)}"
            self.logger.error(error_msg)
            return LLMResponse(
                content="",
                provider=provider,
                model="unknown",
                error=error_msg
            )
    
    async def _generate_openai_response(
        self, 
        prompt: str, 
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None
    ) -> LLMResponse:
        """Generate response using OpenAI"""
        
        model = model or os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        max_tokens = max_tokens or int(os.getenv("OPENAI_MAX_TOKENS", "1000"))
        temperature = temperature or float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = await asyncio.to_thread(
            self.openai_client.chat.completions.create,
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        return LLMResponse(
            content=response.choices[0].message.content,
            provider="openai",
            model=model,
            tokens_used=response.usage.total_tokens if response.usage else None
        )
    
    async def _generate_anthropic_response(
        self, 
        prompt: str, 
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None
    ) -> LLMResponse:
        """Generate response using Anthropic"""
        
        model = model or os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
        max_tokens = max_tokens or int(os.getenv("ANTHROPIC_MAX_TOKENS", "1000"))
        temperature = temperature or float(os.getenv("ANTHROPIC_TEMPERATURE", "0.7"))
        
        # Anthropic uses a different message format
        messages = [{"role": "user", "content": prompt}]
        
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }
        
        if system_prompt:
            kwargs["system"] = system_prompt
        
        response = await asyncio.to_thread(
            self.anthropic_client.messages.create,
            **kwargs
        )
        
        return LLMResponse(
            content=response.content[0].text,
            provider="anthropic",
            model=model,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens if response.usage else None
        )
    
    async def extract_lead_data(self, html_content: str, search_query: str) -> Dict[str, Any]:
        """Extract structured lead data from HTML content using LLM"""
        
        system_prompt = """You are a lead extraction specialist. Your job is to analyze HTML content and extract structured business lead information.

Extract the following information for each business/company found:
- company_name: The business name
- website_url: Company website if available
- contact_email: Email address if found
- contact_name: Contact person name if available
- phone_number: Phone number if found
- industry: Business industry/category
- company_size: Estimated company size (small, medium, large)
- pain_points: Potential business challenges this company might face (infer from context)
- location: Business location/address if available

Return ONLY a valid JSON array of objects, with each object representing one lead. If no leads are found, return an empty array []."""

        user_prompt = f"""Search Query: {search_query}

HTML Content to analyze:
{html_content[:8000]}  # Limit content to avoid token limits

Extract business leads from this content and return as JSON array."""

        response = await self.generate_response(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=2000,
            temperature=0.3  # Lower temperature for more consistent extraction
        )
        
        if response.error:
            self.logger.error(f"LLM extraction failed: {response.error}")
            return {"leads": [], "error": response.error}
        
        try:
            # Try to parse the JSON response
            leads_data = json.loads(response.content)
            if not isinstance(leads_data, list):
                leads_data = []
            
            return {"leads": leads_data, "extracted_count": len(leads_data)}
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM response as JSON: {e}")
            self.logger.debug(f"Raw response: {response.content}")
            return {"leads": [], "error": "Failed to parse LLM response"}
    
    def is_available(self, provider: Optional[str] = None) -> bool:
        """Check if a specific provider is available"""
        provider = provider or self.default_provider
        
        if provider == "openai":
            return self.openai_client is not None
        elif provider == "anthropic":
            return self.anthropic_client is not None
        
        return False

# Global LLM service instance
llm_service = LLMService()
