from __future__ import annotations
from imagen.abstract import ImageGenerationResponse, ImageGenerator, ImageGenerationConfig, ImageGenerationOptions, ImageEditionOptions, ImageGenerationError
import requests
from typing import List, Literal
from utils.utils import get_nearest_aspect_ratio, get_literal_values, download_image
from utils.s3 import copy_url_to_s3
import os
from dataclasses import dataclass
from registery import register_generator


@dataclass
class RunpodNanoBananaGeneratorConfig(ImageGenerationConfig):
    api_key : str

    @classmethod
    def from_config_dict(cls, data: dict | None) -> RunpodNanoBananaGeneratorConfig:
        return cls(
            api_key=os.getenv("RUNPOD_API_KEY", "")
        )

@dataclass
class RunpodNanoBananaImageEditingOptions(ImageEditionOptions):
    prompt : str
    image_urls : List[str]
    resolution : Literal["1k", "2k", "4k"] = "1k"
    aspect_ratio : Literal[
        "1:1",
        "3:2",
        "2:3",
        "3:4",
        "4:3",
        "4:5",
        "5:4",
        "9:16",
        "16:9",
        "21:9"
    ] | None = None

@dataclass
class RunpodNanoBananaResponse(ImageGenerationResponse):
    def __init__(self, response, generator_config: RunpodNanoBananaGeneratorConfig) -> None:
        self.response = response
        
    def url(self) -> str:
        url = self.response["output"]["result"]
        s3_url = copy_url_to_s3(url)
        return s3_url


@register_generator("nanobanana")
class RunpodNanoBananaClient(ImageGenerator) :
    Config = RunpodNanoBananaGeneratorConfig

    def __init__(self, generator_config: RunpodNanoBananaGeneratorConfig) -> None:
        super().__init__(generator_config)

    def edit_image(self, options: RunpodNanoBananaImageEditingOptions) -> ImageGenerationResponse:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.generator_config.api_key}"
        }
        
        if options.aspect_ratio is None:
            allowed_aspect_ratios = get_literal_values(RunpodNanoBananaImageEditingOptions, "aspect_ratio")
            first_image = download_image(options.image_urls[0])
            options.aspect_ratio = get_nearest_aspect_ratio(
                size=first_image.size,
                allowed_ratios=allowed_aspect_ratios
            )
        
        data = {
            'input': {
                "prompt": options.prompt,
                "images": options.image_urls,
                "resolution": options.resolution,
                "output_format": "jpeg",
                "enable_base64_output": False,
                "enable_sync_mode": False
            }
        }
        response = requests.post('https://api.runpod.ai/v2/nano-banana-pro-edit/runsync', headers=headers, json=data)        
        self.response = response.json()
        return RunpodNanoBananaResponse(self.response, self.generator_config)

    @classmethod
    def readme(cls) -> str:
        return """
Nano Banana Pro Prompting Guide
Built on Gemini 3 Pro for image gen/editing in Gemini app, AI Studio, Vertex. Use up to 14 input images.

Establish Vision: Subject, Composition, Action, Location, Style
Be specific: "Stoic robot barista with blue optics brewing coffee in futuristic Mars cafe, 3D animation style."

Refine Details: Camera, Lighting, Aspect Ratio, Text
"Low-angle 9:16 poster, golden hour backlighting f/1.8, 'URBAN EXPLORER' bold white sans-serif top."

Factual Diagrams: Demand Accuracy
"Scientifically precise cross-section of engine, historically accurate Victorian scene."

Reference Inputs Clearly
"Pose from Image A, style from Image B, background from Image C."

Text Rendering: Generate Legible Text
"Poster with 'How much wood would a woodchuck chuck' carved from wood by woodchuck."

Real-World Knowledge: Use Gemini's Expertise
"Infographic: Step-by-step elaichi chai recipe."

Translate/Localize: Adapt Text in Images
"Translate all English on yellow cans to Korean, keep rest identical."

Studio Edits: Control Lighting/Focus
"Turn daytime scene to nighttime." "Refocus on flowers."

Resize Precisely: 1K/2K/4K Ratios
"Adapt to 16:9 cinematic, 21:9 wide."

Blend Images: Consistent Characters/Brands
"Fuse 6-14 images: Mannequin dress from Img2, cinematic 16:9 composite."
"Apply groovy 1970s WAVE logo to 10 mockups: apparel, billboards (16:9 each)."

Limitations: Verify Text Fidelity, Facts, Translations, Complex Blends
Small text/spelling may err; check diagrams; edits can artifact.

Place the most important image first if using a None aspect ratio.
The targeted aspect ratio will be inferred from the first image.
        """

