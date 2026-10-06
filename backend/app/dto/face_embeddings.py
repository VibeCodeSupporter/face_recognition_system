from pydantic import Field, StrictFloat, model_validator

from app.dto.common import DTO, text


class FaceEmbeddingPut(DTO):
    image_url: text(2048) | None = None
    model_name: text(100)
    model_version: text(30)
    dimension: int = Field(strict=True, ge=1, le=4096)
    embedding_data: list[StrictFloat] = Field(min_length=1, max_length=4096)

    @model_validator(mode="after")
    def check_dimension(self):
        if len(self.embedding_data) != self.dimension:
            raise ValueError("Vector length must equal dimension.")
        return self
