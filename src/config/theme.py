#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Central color palette for FiniA application.
#
"""
Central color palette for FiniA application.
Used by both API and any future GUI implementations.
"""

# Central color palette (change here for global theming)
BASE_BACKGROUND_COLOR = "#ffffff"        # App window & general bg
DETAIL_BACKGROUND_COLOR = "#ffffff"      # Transaction details panel bg / surfaces
BORDER_COLOR = "#e0e0e0"                 # Borders and grid lines
TEXT_COLOR = "#111111"                   # Primary text

PRIMARY_ACCENT = "#0078d4"               # Accent (buttons, selection)
PRIMARY_ACCENT_HOVER = "#005a9e"         # Accent hover state
PRIMARY_ACCENT_PRESSED = "#004578"       # Accent pressed state
SELECTED_TEXT_COLOR = "#ffffff"          # Text on selected backgrounds
INPUT_BORDER_COLOR = "#cccccc"           # Default input border

# Semantic colors for amounts
AMOUNT_NEGATIVE_COLOR = "#d32f2f"        # Red for negative amounts/expenses
AMOUNT_POSITIVE_COLOR = "#388e3c"        # Green for positive amounts/income
