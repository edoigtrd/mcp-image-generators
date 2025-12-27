from __future__ import annotations

import inspect
import os
from dataclasses import MISSING, fields, is_dataclass
from typing import Any, Dict, Type, get_type_hints

import registery
from fastmcp import FastMCP
import tomllib

from imagen.abstract import (
    ImageEditionOptions,
    ImageGenerationConfig,
    ImageGenerationOptions,
    ImageGenerationResponse,
    ImageGenerator,
)

def _load_toml_config(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    if tomllib is None:
        raise RuntimeError("tomllib is not available (need Python 3.11+).")
    with open(path, "rb") as f:
        return tomllib.load(f)


def _is_overridden(cls: type, method_name: str) -> bool:
    return method_name in cls.__dict__


def _extract_options_type(method: Any, fallback: type) -> type:
    try:
        hints = get_type_hints(method)
    except Exception:
        hints = getattr(method, "__annotations__", {}) or {}
    return hints.get("options", fallback)


def _instantiate_config(config_type: type) -> Any:
    try:
        return config_type()
    except TypeError as e:
        raise RuntimeError(
            f"Config type {config_type.__name__} must be instantiable with no args. Error: {e}"
        )


def _defaults_from_dataclass(dc_type: type) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for f in fields(dc_type):
        if f.default is not MISSING:
            out[f.name] = f.default
        elif f.default_factory is not MISSING:  # type: ignore[attr-defined]
            out[f.name] = f.default_factory()  # type: ignore[misc]
    return out


def _defaults_from_init_signature(t: type) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    sig = inspect.signature(t.__init__)
    for name, param in sig.parameters.items():
        if name == "self":
            continue
        if param.default is not inspect._empty:
            out[name] = param.default
    return out


def _build_options_object(options_type: type, payload: Dict[str, Any]) -> Any:
    if is_dataclass(options_type):
        defaults = _defaults_from_dataclass(options_type)
        merged = {**defaults, **payload}
        return options_type(**merged)

    defaults = _defaults_from_init_signature(options_type)
    merged = {**defaults, **payload}
    return options_type(**merged)


def _url_from_result(result: Any) -> str:
    if isinstance(result, str):
        return result
    if isinstance(result, ImageGenerationResponse):
        return result.url()
    url_method = getattr(result, "url", None)
    if callable(url_method):
        value = url_method()
        if not isinstance(value, str):
            raise TypeError("url() must return a str")
        return value
    raise TypeError("Generator result must be str or ImageGenerationResponse (or have url())")

def _type_to_str(t: Any) -> str:
    try:
        return str(t).replace("typing.", "")
    except Exception:
        return "Any"


def _options_schema(options_type: type) -> Dict[str, Any]:
    if is_dataclass(options_type):
        props: Dict[str, Any] = {}
        required: list[str] = []

        for f in fields(options_type):
            t = _type_to_str(f.type)
            has_default = (f.default is not MISSING) or (f.default_factory is not MISSING)  # type: ignore[attr-defined]
            default = None
            if f.default is not MISSING:
                default = f.default
            elif f.default_factory is not MISSING:  # type: ignore[attr-defined]
                default = f.default_factory()  # type: ignore[misc]

            props[f.name] = {"type": t, "default": default}
            if not has_default:
                required.append(f.name)

        return {"type": "object", "properties": props, "required": required}

    sig = inspect.signature(options_type.__init__)
    ann = getattr(options_type.__init__, "__annotations__", {}) or {}

    props: Dict[str, Any] = {}
    required: list[str] = []
    for name, param in sig.parameters.items():
        if name == "self":
            continue
        t = _type_to_str(ann.get(name, Any))
        has_default = param.default is not inspect._empty
        default = None if not has_default else param.default
        props[name] = {"type": t, "default": default}
        if not has_default:
            required.append(name)

    return {"type": "object", "properties": props, "required": required}




def build_mcp() -> FastMCP:
    config_path = os.getenv("IMAGESMCP_CONFIG", "config.toml")
    toml_cfg = _load_toml_config(config_path)

    mcp = FastMCP("images-mcp")
    generators: Dict[str, Type[ImageGenerator]] = dict(registery.REGISTERED_GENERATORS)

    def _make_generate_schema_tool(gen_name: str, gen_cls: Type[ImageGenerator]) -> None:
        opt_type = _extract_options_type(gen_cls.generate_image, ImageGenerationOptions)

        def generate_schema() -> Dict[str, Any]:
            return _options_schema(opt_type)

        mcp.tool(name=f"image-{gen_name}-generate_schema")(generate_schema)

    def _make_edit_schema_tool(gen_name: str, gen_cls: Type[ImageGenerator]) -> None:
        opt_type = _extract_options_type(gen_cls.edit_image, ImageEditionOptions)

        def edit_schema() -> Dict[str, Any]:
            return _options_schema(opt_type)

        mcp.tool(name=f"image-{gen_name}-edit_schema")(edit_schema)

    @mcp.tool(name="image-list")
    def list_generators() -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for name, cls in generators.items():
            out[name] = {
                "class": f"{cls.__module__}.{cls.__name__}",
                "capabilities": {
                    "generate": _is_overridden(cls, "generate_image"),
                    "edit": _is_overridden(cls, "edit_image"),
                },
            }
        return out

    for gen_name, gen_cls in generators.items():
        config_type = getattr(gen_cls, "Config", ImageGenerationConfig)

        raw_section = toml_cfg.get(config_type.__name__)
        config_section = raw_section if isinstance(raw_section, dict) else None

        if hasattr(config_type, "from_config_dict") and callable(getattr(config_type, "from_config_dict")):
            cfg = config_type.from_config_dict(config_section)
        else:
            cfg = config_type(**(config_section or {}))

        gen = gen_cls(cfg)

        def _make_readme_tool(gen_name: str, gen_cls: Type[ImageGenerator]) -> None:
            def readme() -> str:
                fn = getattr(gen_cls, "readme", None)
                if callable(fn):
                    return str(fn())
                return (gen_cls.__doc__ or "").strip() or "No README available."
            mcp.tool(name=f"image-{gen_name}-readme")(readme)

        def _make_generate_tool(gen_name: str, gen: ImageGenerator, gen_cls: Type[ImageGenerator]) -> None:
            opt_type = _extract_options_type(gen_cls.generate_image, ImageGenerationOptions)

            def generate(options: Dict[str, Any]) -> str:
                opt_obj = _build_options_object(opt_type, options)
                result = gen.generate_image(opt_obj)
                return _url_from_result(result)

            mcp.tool(name=f"image-{gen_name}-generate")(generate)

        def _make_edit_tool(gen_name: str, gen: ImageGenerator, gen_cls: Type[ImageGenerator]) -> None:
            opt_type = _extract_options_type(gen_cls.edit_image, ImageEditionOptions)

            def edit(options: Dict[str, Any]) -> str:
                opt_obj = _build_options_object(opt_type, options)
                result = gen.edit_image(opt_obj)
                return _url_from_result(result)

            mcp.tool(name=f"image-{gen_name}-edit")(edit)

        _make_readme_tool(gen_name, gen_cls)

        if _is_overridden(gen_cls, "generate_image"):
            _make_generate_schema_tool(gen_name, gen_cls)
            _make_generate_tool(gen_name, gen, gen_cls)

        if _is_overridden(gen_cls, "edit_image"):
            _make_edit_schema_tool(gen_name, gen_cls)
            _make_edit_tool(gen_name, gen, gen_cls)

    return mcp



def main() -> None:
    transport = os.getenv("MCP_TRANSPORT", "http").lower()
    mcp = build_mcp()

    if transport == "http":
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "7001"))
        mcp.run(transport="http", host=host, port=port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
