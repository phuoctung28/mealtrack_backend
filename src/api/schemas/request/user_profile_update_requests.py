from pydantic import BaseModel, Field
from enum import Enum


class GoalEnum(str, Enum):
    maintenance = "maintenance"
    cutting = "cutting"
    bulking = "bulking"


class UpdateFitnessGoalRequest(BaseModel):
    goal: GoalEnum = Field(..., description="New fitness goal")
    override: bool = Field(False, description="Allow bypassing cooldown guardrail")


