from pydantic import BaseModel, Field

try:
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover - Pydantic v1
    ConfigDict = None


class PredictionResult(BaseModel):
    if ConfigDict is not None:
        model_config = ConfigDict(populate_by_name=True)
    else:
        class Config:
            allow_population_by_field_name = True

    model: str
    probability: float = Field(ge=0.0, le=1.0)
    prediction: int = Field(ge=0, le=1)
    class_name: str = Field(alias="class")
    inference_time: float

    def model_dump(self, *args, **kwargs):
        base_model_dump = getattr(super(), "model_dump", None)
        if callable(base_model_dump):
            return base_model_dump(*args, **kwargs)
        return self.dict(*args, **kwargs)
