from dataclasses import dataclass


@dataclass
class UpdateUserGoalCommand:
    user_id: str
    goal: str  # maintenance | cutting | bulking
    override: bool = False  # bypass cooldown when True


