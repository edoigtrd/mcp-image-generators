import requests
from PIL import Image
import io
import base64
from math import gcd
from typing import get_type_hints, get_origin, get_args, Literal


def get_literal_values(cls: type, field_name: str) -> list[object]:
    hints = get_type_hints(cls, include_extras=True)
    ann = hints[field_name]

    # Handle Optional / unions like Literal[...] | None
    origin = get_origin(ann)
    if origin is type(None):
        return []
    if origin is None:
        # Might be Literal directly
        if get_origin(ann) is Literal:
            return list(get_args(ann))
        return []

    # Union case (Literal[...] | None) => origin is types.UnionType (py3.10+) or typing.Union
    if origin in (list, dict, tuple, set):
        return []

    # Union / | case
    if origin is getattr(__import__("types"), "UnionType", object()) or str(origin).endswith("typing.Union"):
        out: list[object] = []
        for part in get_args(ann):
            if part is type(None):
                continue
            if get_origin(part) is Literal:
                out.extend(get_args(part))
        return out

    # Direct Literal
    if origin is Literal:
        return list(get_args(ann))

    return []

def image_to_b64(image: Image.Image) -> str:
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str


def download_image(url) -> Image.Image:
    response = requests.get(url)
    image = Image.open(io.BytesIO(response.content))
    return image


def get_ratio(image: Image.Image) :
    w, h = image.size
    g = gcd(w, h)
    ratio = f"{w//g}:{h//g}"
    return ratio

def concat_images_side_by_side(images) -> Image.Image:
    # images: list of PIL.Image
    if not images:
        return None
    
    w, h = images[0].size

    # Hauteur de référence = celle de la première image
    target_height = h
    resized = []
    for img in images:
        ow, oh = img.size
        new_w = int(ow * target_height / oh)
        resized.append(img.resize((new_w, target_height), Image.LANCZOS))

    total_width = sum(im.width for im in resized)
    new_img = Image.new("RGB", (total_width, target_height))

    x_offset = 0
    for im in resized:
        new_img.paste(im, (x_offset, 0))
        x_offset += im.width

    return new_img

def get_nearest_aspect_ratio(size: tuple[int, int] , allowed_ratios:list[str]) -> str:
    w, h = size
    target_ratio = w / h

    def ratio_value(ratio_str: str) -> float:
        rw, rh = map(int, ratio_str.split(":"))
        return rw / rh

    nearest_ratio = min(allowed_ratios, key=lambda r: abs(ratio_value(r) - target_ratio))
    return nearest_ratio