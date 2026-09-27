"""Canonical Pydantic contracts for the deterministic Memory Spread renderer."""

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Gutter(ContractModel):
    x: Literal[776] = 776
    width: Literal[48] = 48


class Canvas(ContractModel):
    width: Literal[1600] = 1600
    height: Literal[1000] = 1000
    page_split_x: Literal[800] = 800
    outer_safe_margin: Literal[48] = 48
    gutter: Gutter = Field(default_factory=Gutter)


class Bounds(ContractModel):
    x: float
    y: float
    width: float = Field(gt=0)
    height: float = Field(gt=0)


class RectangleMask(ContractModel):
    kind: Literal["rectangle"]


class RoundedRectangleMask(ContractModel):
    kind: Literal["rounded_rectangle"]
    radius_px: float = Field(ge=0)


class EllipseMask(ContractModel):
    kind: Literal["ellipse"]


class MaskPoint(ContractModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class PolygonMask(ContractModel):
    kind: Literal["polygon"]
    points: list[MaskPoint] = Field(min_length=3)


class SvgPathMask(ContractModel):
    kind: Literal["svg_path"]
    # Path coordinates use the element's local canonical pixel space.
    path: str = Field(min_length=1)


class AlphaMask(ContractModel):
    kind: Literal["alpha_mask"]
    asset_ref: str = Field(min_length=1)


ElementMask = Annotated[
    Union[RectangleMask, RoundedRectangleMask, EllipseMask, PolygonMask, SvgPathMask, AlphaMask],
    Field(discriminator="kind"),
]
SourceId = Annotated[str, Field(min_length=1)]


class ElementBase(ContractModel):
    id: str = Field(min_length=1)
    bounds: Bounds
    rotation_deg: float = 0
    z_index: int
    provenance_interactive: bool
    overlap_group_id: Annotated[str, Field(min_length=1)] | None = None


class SourceElement(ElementBase):
    source_ids: list[SourceId] = Field(min_length=1)
    provenance_interactive: Literal[True] = True


class MaskedElement(SourceElement):
    mask: ElementMask | None = None
    original_region_mask: ElementMask | None = None


class PhotoElement(MaskedElement):
    kind: Literal["photo"]
    source_asset_id: str = Field(min_length=1)
    treatment: Literal["PRESERVE", "ANNOTATE", "EXTEND"]
    fit: Literal["cover", "contain"]


class TextElement(SourceElement):
    kind: Literal["text"]
    text: str
    text_mode: Literal["verbatim", "refined"]
    style_role: Literal["title", "body", "quote", "caption"]
    font_size_px: int = Field(ge=20)
    align: Literal["left", "center", "right"]


class AudioElement(SourceElement):
    kind: Literal["audio"]
    clip_start_ms: int = Field(ge=0)
    clip_end_ms: int = Field(gt=0)
    transcript_excerpt: str | None = None


class GeneratedAssetElement(MaskedElement):
    kind: Literal["generated_asset"]
    treatment: Literal["ANNOTATE", "EXTEND", "DISTILL"]
    art_style: Literal["tape_collage", "gathered_scenes", "doodle"]
    asset_request_id: str = Field(min_length=1)
    asset_ref: str = Field(min_length=1)
    generation_mode: Literal["live", "cache", "fallback"]


class DecorationElement(ElementBase):
    kind: Literal["decoration"]
    chrome_kind: Literal["paper", "gutter", "page_shadow", "generic_mount"]
    provenance_interactive: Literal[False] = False


VisualElement = Annotated[
    Union[
        PhotoElement,
        TextElement,
        AudioElement,
        GeneratedAssetElement,
        DecorationElement,
    ],
    Field(discriminator="kind"),
]


class ResolvedVisualPlan(ContractModel):
    schema_version: str
    plan_id: str
    plan_revision: int = Field(ge=1)
    session_id: str
    canvas: Canvas
    title: str
    palette: list[str] = Field(min_length=2)
    uses_timeline: bool
    status: Literal["resolved"]
    elements: list[VisualElement] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_renderer_contract(self) -> "ResolvedVisualPlan":
        safe = self.canvas.outer_safe_margin
        gutter_left = self.canvas.gutter.x
        gutter_right = gutter_left + self.canvas.gutter.width

        if len({element.id for element in self.elements}) != len(self.elements):
            raise ValueError("element IDs must be unique")

        for element in self.elements:
            bounds = element.bounds
            if bounds.x < 0 or bounds.y < 0:
                raise ValueError(f"{element.id} starts outside the canvas")
            if bounds.x + bounds.width > self.canvas.width:
                raise ValueError(f"{element.id} exceeds the canvas width")
            if bounds.y + bounds.height > self.canvas.height:
                raise ValueError(f"{element.id} exceeds the canvas height")

            if element.kind in {"text", "audio"}:
                if bounds.x < safe or bounds.y < safe:
                    raise ValueError(f"{element.id} violates the outer safe margin")
                if bounds.x + bounds.width > self.canvas.width - safe:
                    raise ValueError(f"{element.id} violates the outer safe margin")
                if bounds.y + bounds.height > self.canvas.height - safe:
                    raise ValueError(f"{element.id} violates the outer safe margin")
                crosses_gutter = bounds.x < gutter_right and bounds.x + bounds.width > gutter_left
                if crosses_gutter:
                    raise ValueError(f"{element.id} intersects the center gutter")

            if element.kind == "audio" and (
                bounds.width < 44 or bounds.height < 44
            ):
                raise ValueError(f"{element.id} is smaller than the audio target minimum")

            if element.kind == "audio" and element.clip_end_ms <= element.clip_start_ms:
                raise ValueError(f"{element.id} has an invalid audio range")
            if element.kind in {"photo", "generated_asset"}:
                if element.treatment == "EXTEND" and element.original_region_mask is None:
                    raise ValueError(f"{element.id} requires an original_region_mask")

        for index, element in enumerate(self.elements):
            a = element.bounds
            for other in self.elements[index + 1:]:
                b = other.bounds
                overlaps = (a.x < b.x + b.width and a.x + a.width > b.x
                            and a.y < b.y + b.height and a.y + a.height > b.y)
                if overlaps and not (element.overlap_group_id and
                                     element.overlap_group_id == other.overlap_group_id):
                    raise ValueError(f"{element.id} and {other.id} overlap without a shared group")

        return self
