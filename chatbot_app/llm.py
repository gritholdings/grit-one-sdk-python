from openai import OpenAI
from enum import Enum


class OpenaiModel(Enum):
    GPT_3_5 = "gpt-3.5-turbo"
    GPT_4 = "gpt-4-turbo"

    @classmethod
    def choices(cls):
        return [(key.name, key.value) for key in cls]


class OpenaiAdapter:
    """Openai Adapter"""
    def __init__(self):
        # it will access the API key from os.environ
        self.client = OpenAI()

    def chat(self, model: OpenaiModel = OpenaiModel.GPT_3_5, messages: list = []):
        formatted_messages = [
            {"role": "system", "content": "You are a helpful assistant."}
        ]
        formatted_messages.extend(messages)
        completion = self.client.chat.completions.create(
            model=model.value,
            messages=formatted_messages
        )
        return completion.choices[0].message.content


openai_instance = OpenaiAdapter()