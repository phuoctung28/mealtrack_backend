from pydantic import BaseModel, Field


class SimpleMacroTargets(BaseModel):
    """
    Simplified macro targets class for frontend use.
    Contains only the essential macronutrients: protein, carbs, and fat.
    """
    protein: float = Field(..., description="Protein target in grams", ge=0)
    carbs: float = Field(..., description="Carbohydrates target in grams", ge=0)
    fat: float = Field(..., description="Fat target in grams", ge=0)
    
    class Config:
        schema_extra = {
            "example": {
                "protein": 150.0,
                "carbs": 200.0,
                "fat": 65.0
            }
        }
    
    @property
    def total_calories(self) -> float:
        """Calculate total calories from macros"""
        return (self.protein * 4) + (self.carbs * 4) + (self.fat * 9)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for easy JSON serialization"""
        return {
            "protein": self.protein,
            "carbs": self.carbs,
            "fat": self.fat
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MacroTargets":
        """Create MacroTargets from dictionary"""
        return cls(
            protein=data.get("protein", 0),
            carbs=data.get("carbs", 0),
            fat=data.get("fat", 0)
        )