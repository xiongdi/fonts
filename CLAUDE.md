# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Font merging tool that combines Chinese and English fonts. Merges a base Chinese font with English fonts to produce combined fonts that display both Chinese and English characters with the English font's glyphs.

## Commands

Run the font merge tool:
```bash
python font_merge.py
```

Output files are generated in the `output/` directory (OTF and WOFF2 formats).

## Configuration

Edit `pyproject.toml` `[tool.font-merge]` section to configure:
- `chinese-fonts`: Base Chinese fonts (supports TTC with index)
- `english-fonts`: English fonts to merge
- `output-dir`: Output directory

## Architecture

Single-file Python script (`font_merge.py`):
- Uses `fonttools` library for font manipulation
- Extracts glyphs from both fonts using `pyftsubset`
- Merges by adding English glyphs to Chinese font base
- Replaces ASCII character mappings with English font's glyphs
- Deletes vertical metrics tables (vhea, vmtx, VDMX) to ensure WOFF2 compatibility
