# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Font merging tool that combines Chinese and English fonts. Takes a Chinese base font and merges English monospace font glyphs into it, replacing ASCII characters with the English font's glyphs for better code display.

## Commands

```bash
python main.py download              # Download fonts to cache
python main.py build                 # Build all (incremental)
python main.py build --profile dev   # Build by profile
python main.py build LXGWWenKai FiraCode  # Build specific combination
python main.py install               # Install all to system
python main.py install LXGWWenKai+FiraCode  # Install specific font
python main.py uninstall             # Uninstall from system
python main.py clean                 # Clean output directory
python main.py list                  # List available fonts
```

Output: `fonts/output/` (OTF). Cache: `fonts/cache/`.

## Configuration

Edit `pyproject.toml` `[tool.font-merge]` section:
- `chinese-fonts`: Base Chinese fonts (TTC files need `index`)
- `english-fonts`: English monospace fonts to merge
- `output-dir`: Output directory
- `cache-dir`: Cache directory for downloaded fonts

Each font entry supports:
- `name`: Font name for output
- `github`: GitHub repository URL
- `download`: Direct download URL (ZIP, 7z, or TTF/OTF)
- `stars`: GitHub stars count

**Important:** Do NOT modify the font source lists (chinese-fonts, english-fonts) in pyproject.toml unless explicitly requested. Profiles can be customized for different build scopes.

## Architecture

Modular Python project with manifest-driven incremental builds:

- `main.py` — CLI entry point
- `config.py` — Configuration management
- `manifest.py` — Build manifest (tracks source/output state for incremental builds)
- `downloader.py` — Phase 1: Download fonts to cache
- `merger.py` — Phase 2: Merge fonts (parallel, incremental)
- `installer.py` — Phase 3/4: Install/Uninstall fonts to system

### Build Process

1. `python main.py download` — Download fonts to `fonts/cache/`
2. `python main.py build` — Merge fonts (manifest-driven, only rebuilds changed)
3. `python main.py install` — Install to system fonts

### Incremental Builds

`fonts/manifest.json` tracks source mtime/size and output state. Only rebuilds combinations when source fonts change.

### Profiles

`pyproject.toml` defines profiles (e.g., `dev` for fast testing, `full` for all combinations):

### CFF Font Handling

CFF fonts (PostScript outlines) are detected via `has_cff_table()`. When detected:
- Attempt conversion to TTF via `pyftsubset --format=ttf`
- If conversion fails, glyph replacement is skipped — only cmap remapping occurs
- This is a known limitation since fonttools cannot copy CFF glyphs between fonts

### Cache Strategy

`find_font_in_cache()` searches for fonts with priority: `Regular` > `Normal` > best match. Archive extraction uses 7z or ZIP depending on file extension.

## Dependencies

- Python 3.14+
- fonttools (for TTFont manipulation and pyftsubset)
- httpx (for font downloads)
- py7zr (for 7z archive extraction)

## Repository Hygiene

Test output files (`.ttf`, `.cff`) in the repo root are from development — do not commit these to version control.

---

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
