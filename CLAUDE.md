# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Font merging tool that combines Chinese and English fonts. Takes a Chinese base font and merges English monospace font glyphs into it, replacing ASCII characters with the English font's glyphs for better code display.

## Commands

Run the font merge tool:
```bash
python font_merge.py
```

Output files are generated in `output/` directory (OTF format). Downloaded fonts are cached in `cache/`.

## Configuration

Edit `pyproject.toml` `[tool.font-merge]` section:
- `chinese-fonts`: Base Chinese fonts (TTC files need `index`)
- `english-fonts`: English monospace fonts to merge
- `output-dir`: Output directory
- `cache-dir`: Cache directory for downloaded fonts

Each font entry supports:
- `name`: Font name for output
- `github`: GitHub repository URL
- `download`: Direct download URL (ZIP or TTF/OTF)
- `stars`: GitHub stars count

**Important:** Do NOT modify the font list (chinese-fonts and english-fonts arrays) in pyproject.toml unless explicitly requested by the user.

## Architecture

Single-file Python script (`font_merge.py`):

1. **Config loading**: Reads `pyproject.toml` using `tomllib`
2. **Font resolution**: Downloads remote fonts via `httpx`, extracts ZIPs, caches locally
3. **Merge process**:
   - Uses `pyftsubset` to extract glyph subsets
   - Loads fonts with `fontTools.ttLib.TTFont`
   - Adds English glyphs to Chinese font base
   - Replaces ASCII character mappings (0x00-0xFF)
   - Deletes vertical metrics tables (`vhea`, `vmtx`, `VDMX`) to ensure compatibility
   - Updates `maxp.numGlyphs` and `hhea.numberOfHMetrics`
4. **Output**: Saves OTF files with merged font name

## Font Sources

Current configuration uses GitHub Stars ranked fonts:
- Chinese: LXGW WenKai, Source Han Sans, Smiley Sans, Source Han Serif, Noto CJK
- English: Fira Code, Cascadia Code, Maple Font, Iosevka, Source Code Pro, etc. (top 20 monospace)

## Dependencies

- Python 3.14+
- fonttools (for TTFont manipulation)
- httpx (for font downloads)
- pyftsubset (bundled with fonttools, used via subprocess)
