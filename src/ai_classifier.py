"""
AI classification functionality for PhishFish application.
"""

import json
from pathlib import Path

from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

from config import config


class EmailClassifier:
    """Handles AI-based email classification."""

    def __init__(self):
        """Initialize the AI client."""
        self.client = ChatCompletionsClient(
            endpoint=config.AZURE_ENDPOINT,
            credential=AzureKeyCredential(config.GITHUB_TOKEN),
        )
        self._load_system_prompt()

    def _load_system_prompt(self):
        """Load the system prompt from file."""
        prompt_path = Path(__file__).resolve().parent / "system-prompt.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.system_prompt = f.read().strip()

    def classify_email(self, email_content):
        """Use Azure AI to classify the email and return JSON result."""
        try:
            response = self.client.complete(
                messages=[
                    SystemMessage(self.system_prompt),
                    UserMessage(email_content),
                ],
                temperature=0.0,
                top_p=1.0,
                model=config.AZURE_MODEL,
            )
        except Exception as e:
            raise RuntimeError(f"AI classification failed: {e}") from e

        content = response.choices[0].message.content.strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError as je:
            raise RuntimeError(
                f"Invalid JSON from AI: {je}\nContent was: {content}"
            ) from je


# Global classifier instance
classifier = EmailClassifier()
