"""Structured schemas used by the OpenAI translation adapter."""

from pydantic import BaseModel, Field


class OpenAITranslationItem(BaseModel):
    index: int = Field(ge=0)
    text: str = Field(min_length=1)


class OpenAITranslationBatch(BaseModel):
    items: list[OpenAITranslationItem]
