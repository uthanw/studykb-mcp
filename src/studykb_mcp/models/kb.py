"""Knowledge base data models."""

from pydantic import BaseModel


class Material(BaseModel):
    """A material file in the knowledge base."""

    name: str  # File name without extension
    line_count: int
    has_index: bool


class Category(BaseModel):
    """A category (folder) in the knowledge base."""

    name: str
    materials: list[Material]

    @property
    def file_count(self) -> int:
        """Get the number of materials in this category."""
        return len(self.materials)
