"""
Centralized mapper for job types and fitness goals.
Ensures consistent mapping across the entire application.
"""

from typing import Dict

from src.domain.model.user import JobType, Goal, TrainingLevel


class ActivityGoalMapper:
    """Centralized mapper for job types and fitness goals."""

    # Job type mappings - all variations map to canonical enum values
    JOB_TYPE_MAP: Dict[str, JobType] = {
        # Canonical values
        "desk": JobType.DESK,
        "on_feet": JobType.ON_FEET,
        "physical": JobType.PHYSICAL,
        # Alternative names
        "sitting": JobType.DESK,
        "standing": JobType.ON_FEET,
        "manual_labor": JobType.PHYSICAL,
    }

    # Goal mappings - canonical values only (mobile migration complete)
    GOAL_MAP: Dict[str, Goal] = {
        "cut": Goal.CUT,
        "bulk": Goal.BULK,
        "recomp": Goal.RECOMP,
    }

    # Training level mappings
    TRAINING_LEVEL_MAP: Dict[str, TrainingLevel] = {
        "beginner": TrainingLevel.BEGINNER,
        "intermediate": TrainingLevel.INTERMEDIATE,
        "advanced": TrainingLevel.ADVANCED,
    }

    @classmethod
    def map_job_type(cls, job_type: str | None) -> JobType:
        """Map job type string to enum, with fallback to DESK."""
        if not job_type:
            return JobType.DESK
        return cls.JOB_TYPE_MAP.get(job_type.lower(), JobType.DESK)

    @classmethod
    def map_goal(cls, goal: str | None) -> Goal:
        """Map goal string to enum, with fallback to RECOMP."""
        if not goal:
            return Goal.RECOMP
        return cls.GOAL_MAP.get(goal.lower(), Goal.RECOMP)

    @classmethod
    def map_training_level(cls, training_level: str | None) -> TrainingLevel:
        """Map training level string to enum, with fallback to BEGINNER."""
        if not training_level:
            return TrainingLevel.BEGINNER
        return cls.TRAINING_LEVEL_MAP.get(
            training_level.lower(), TrainingLevel.BEGINNER
        )
