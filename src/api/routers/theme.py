"""
Theme/Style API router for frontend styling
"""

from fastapi import APIRouter
from api.models import ColorPaletteResponse

# Import color constants from central theme configuration
from config.theme import (
    BASE_BACKGROUND_COLOR,
    DETAIL_BACKGROUND_COLOR,
    BORDER_COLOR,
    TEXT_COLOR,
    PRIMARY_ACCENT,
    PRIMARY_ACCENT_HOVER,
    PRIMARY_ACCENT_PRESSED,
    SELECTED_TEXT_COLOR,
    INPUT_BORDER_COLOR,
    AMOUNT_NEGATIVE_COLOR,
    AMOUNT_POSITIVE_COLOR
)

router = APIRouter(prefix="/theme", tags=["theme"])


@router.get("/colors", response_model=ColorPaletteResponse)
def get_color_palette():
    """
    Get the centralized color palette for frontend theming.
    
    Returns the same colors used in the PyQt6 GUI, ensuring consistent branding.
    """
    return ColorPaletteResponse(
        baseBackground=BASE_BACKGROUND_COLOR,
        detailBackground=DETAIL_BACKGROUND_COLOR,
        border=BORDER_COLOR,
        textColor=TEXT_COLOR,
        primaryAccent=PRIMARY_ACCENT,
        primaryAccentHover=PRIMARY_ACCENT_HOVER,
        primaryAccentPressed=PRIMARY_ACCENT_PRESSED,
        selectedText=SELECTED_TEXT_COLOR,
        inputBorder=INPUT_BORDER_COLOR,
        amountNegative=AMOUNT_NEGATIVE_COLOR,
        amountPositive=AMOUNT_POSITIVE_COLOR
    )


@router.get("/css")
def get_css_variables():
    """
    Get color palette as CSS custom properties (variables).
    
    Returns a CSS string that can be injected into the frontend.
    """
    css = f"""
:root {{
    --color-bg-base: {BASE_BACKGROUND_COLOR};
    --color-bg-detail: {DETAIL_BACKGROUND_COLOR};
    --color-border: {BORDER_COLOR};
    --color-text: {TEXT_COLOR};
    --color-accent: {PRIMARY_ACCENT};
    --color-accent-hover: {PRIMARY_ACCENT_HOVER};
    --color-accent-pressed: {PRIMARY_ACCENT_PRESSED};
    --color-text-selected: {SELECTED_TEXT_COLOR};
    --color-input-border: {INPUT_BORDER_COLOR};
    --color-amount-negative: {AMOUNT_NEGATIVE_COLOR};
    --color-amount-positive: {AMOUNT_POSITIVE_COLOR};
}}
"""
    return {"css": css.strip()}
