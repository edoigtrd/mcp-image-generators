from __future__ import annotations
from imagen.abstract import ImageGenerationResponse, ImageGenerator, ImageGenerationConfig, ImageGenerationOptions, ImageEditionOptions, ImageGenerationError
import requests
from typing import Literal
from utils.utils import download_image
from utils.s3 import copy_url_to_s3
from PIL import Image
import time
from dataclasses import dataclass
from registery import register_generator
import os


@dataclass
class FluxImageGeneratorConfig(ImageGenerationConfig):
    api_key : str

    @classmethod
    def from_config_dict(cls, data: dict | None) -> FluxImageGeneratorConfig:
        return cls(
            api_key=os.getenv("BFL_API_KEY", "")
        )

@dataclass
class FluxImageGeneratorOptions(ImageGenerationOptions):
    prompt : str
    model : Literal[
        "flux-2-max",
        "flux-2-pro",
        "flux-2-flex",
        "flux-kontext-max",
        "flux-kontext-pro",
        "flux-pro-1.1-ultra",
        "flux-pro-1.1",
        "flux-pro",
        "flux-dev"
    ] = "flux-2-max"
    aspect_ratio : Literal[
        "1:1",
        "16:9",
        "9:16",
        "4:3",
        "21:9"
    ] = "1:1"

class FluxImageEditionOptions(ImageEditionOptions):
    pass

class FluxResponse(ImageGenerationResponse):
    def __init__(self, response, generator_config: FluxImageGeneratorConfig) -> None:
        self.response = response
        self.image = None
        self.polling_url = response.get("polling_url")
        self.request_id = response.get("id")
        self.retriveal_url = None
        self.generator_config = generator_config

    def _retrieve_image(self) -> Image.Image:
        if self.retriveal_url is not None:
            self.image = download_image(self.retriveal_url)
        return self.image

    def _pool(self) -> bool:
        """Returns False if still processing, True if done"""
        result = requests.get(
            self.polling_url,
            headers={
                "accept": "application/json",
                "x-key": self.generator_config.api_key,
            },
            params={
                "id": self.request_id,
            },
        ).json()
        status = result.get("status")
        if status in ["Failed", "Error"]:
            return False
        if status == "Ready":
            self.retriveal_url = result["result"]["sample"]
            return True
        return False

    def pool(self, auto=True):
        if self.image is not None:
            return self.image
        if self.polling_url is None:
            raise ImageGenerationError("No polling url found")
        if auto:
            while not self._pool():
                time.sleep(1)
        else:
            self._pool()
        return self._retrieve_image()
    
    def url(self) -> str:
        self.pool(auto=True)
        s3_url = copy_url_to_s3(self.retriveal_url)
        return s3_url

@register_generator("flux")
class FluxClient(ImageGenerator):
    Config = FluxImageGeneratorConfig

    def __init__(self, generator_config: FluxImageGeneratorConfig) -> None:
        super().__init__(generator_config)


    def generate_image(self, options: FluxImageGeneratorOptions) -> str:
        request = requests.post(
            "https://api.bfl.ai/v1/{}".format(options.model),
            headers={
                "accept": "application/json",
                "x-key": self.generator_config.api_key,
                "Content-Type": "application/json",
            },
            json={"prompt": options.prompt, "aspect_ratio": options.aspect_ratio},
        )

        if request.status_code == 429:
            raise ImageGenerationError("Rate limit exceeded")
        if request.status_code == 402:
            raise ImageGenerationError("Out of credits")

        fr = FluxResponse(request.json(), self.generator_config)
        return fr
    
    @classmethod
    def readme(cls) -> str:
        return """
Structure for Control
Use JSON structured prompts when you need precise control over multiple elements. Start simple and add complexity as needed.

Be Specific with Colors
Always associate hex codes with specific objects. “The car is #FF0000” works better than “use red #FF0000 in the image.”

Describe What You Want
FLUX.2 has no negative prompts. Instead of “no blur,” say “sharp focus throughout.” Instead of “no people,” describe an “empty scene.”

Reference Camera and Style
For photorealism, specify camera models, lenses, and film stocks. “Shot on Fujifilm X-T5, 35mm f/1.4” produces more authentic results than “professional photo.”

Use Native Languages
Prompt in the language that best describes your desired cultural context. French for Parisian scenes, Japanese for anime styles.

Layer Multi-Reference Carefully
When using multiple input images, clearly describe the role of each: subject from image 1, style from image 2, background from image 3.
        """
