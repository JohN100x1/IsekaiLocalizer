from random import randint
from typing import Self
from uuid import uuid4

from requests import post


class OraAPI:
    system_prompt = (
        "You are ChatGPT, a large language model trained by OpenAI. "
        "Answer as concisely as possible"
    )
    description = "ChatGPT Openai Language Model"
    slug = "gpt-3.5"
    model = "gpt-3.5-turbo"

    def __init__(self, chat_id: str, created_by: str, created_at: str):
        self.chat_id = chat_id
        self.createdBy = created_by
        self.createdAt = created_at

    @classmethod
    def create(cls) -> Self:
        response_json = post(
            "https://ora.sh/api/assistant",
            headers={
                "Origin": "https://ora.sh",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/112.0",
                "Referer": "https://ora.sh/",
                "Host": "ora.sh",
            },
            json={
                "prompt": cls.system_prompt,
                "userId": f"auto:{uuid4()}",
                "name": cls.slug,
                "description": cls.description,
            },
        ).json()
        return OraAPI(
            chat_id=response_json["id"],
            created_by=response_json["createdBy"],
            created_at=response_json["createdAt"],
        )

    def chat(self, prompt: str) -> str:
        response = post(
            "https://ora.sh/api/conversation",
            headers={
                "host": "ora.sh",
                "authorization": f"Bearer AY0{randint(1111, 9999)}",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/112.0",
                "origin": "https://ora.sh",
                "referer": "https://ora.sh/chat/",
            },
            json={
                "chatbotId": self.chat_id,
                "input": prompt,
                "userId": self.createdBy,
                "model": self.model,
                "provider": "OPEN_AI",
                "includeHistory": False,
            },
        ).json()

        return response["response"]
