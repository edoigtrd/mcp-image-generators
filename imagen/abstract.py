from abc import ABC
from dataclasses import dataclass

@dataclass
class ImageGenerationConfig:
    @classmethod
    def from_config_dict(cls, data: dict | None) -> "ImageGenerationConfig":
        pass

@dataclass
class ImageGenerationOptions :
    pass

@dataclass
class ImageEditionOptions :
    pass

@dataclass
class ImageGenerationResponse :
    def url(self) -> str:
        raise NotImplementedError("Subclasses must implement this method.")

class ImageGenerationError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)

class ImageGenerator(ABC):
    def __init__(self, generator_config : ImageGenerationConfig) -> None:
        super().__init__()
        self.generator_config = generator_config
    
    def generate_image(self, options : ImageGenerationOptions) -> ImageGenerationResponse :
        raise NotImplementedError("Subclasses must implement this method.")

    def edit_image(self, options : ImageEditionOptions) -> ImageGenerationResponse :
        raise NotImplementedError("Subclasses must implement this method.")

    @classmethod
    def readme(cls) -> str:
        return "No README available for this generator, please proceed."