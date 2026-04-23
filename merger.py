#!/usr/bin/env python3
"""Phase 2: 合并字体"""
import os
import subprocess
import tempfile
import shutil
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from fontTools.ttLib import TTFont

MAX_WORKERS = os.cpu_count() or 4


def format_size(path: str) -> float:
    return os.path.getsize(path) / 1024


def has_cff_table(font_path: str) -> bool:
    try:
        f = TTFont(font_path, fontNumber=0) if font_path.endswith('.ttc') else TTFont(font_path)
        result = 'CFF ' in f
        f.close()
        return result
    except:
        return False


def ensure_ttf_font(font_path: str, temp_dir: str) -> str:
    if not has_cff_table(font_path):
        return font_path

    base_name = os.path.splitext(os.path.basename(font_path))[0]
    ttf_path = os.path.join(temp_dir, f"{base_name}_converted.ttf")

    if os.path.exists(ttf_path):
        return ttf_path

    print(f"  Converting CFF to TTF...")
    try:
        result = subprocess.run(
            ['pyftsubset', font_path, '--glyphs=*', f'--output-file={ttf_path}',
             '--format=ttf', '--ignore-missing-glyphs', '--ignore-missing-unicodes'],
            capture_output=True, timeout=300
        )
        if result.returncode == 0 and os.path.exists(ttf_path):
            if not has_cff_table(ttf_path):
                return ttf_path
            else:
                print(f"  Warning: Converted file is still CFF")
    except Exception as e:
        print(f"  Convert failed: {e}")

    print(f"  Warning: CFF conversion failed, using original")
    return font_path


def merge_single(en_path: str, zh_path: str, zh_index: int, output_name: str, output_dir: str):
    """合并单个字体组合"""
    td = tempfile.mkdtemp()
    try:
        en_is_ttc = en_path.endswith('.ttc')
        zh_is_ttc = zh_path.endswith('.ttc')

        zh_is_cff = has_cff_table(zh_path) if not zh_is_ttc else False
        en_is_cff = has_cff_table(en_path) if not en_is_ttc else False

        if zh_is_cff:
            zh_path_ttf = ensure_ttf_font(zh_path, td)
            if zh_path_ttf != zh_path and os.path.exists(zh_path_ttf):
                zh_path = zh_path_ttf
                zh_is_cff = False

        if en_is_cff:
            en_path_ttf = ensure_ttf_font(en_path, td)
            if en_path_ttf != en_path and os.path.exists(en_path_ttf):
                en_path = en_path_ttf
                en_is_cff = False

        en = TTFont(en_path, lazy=True, fontNumber=0)
        new_font = TTFont(zh_path, lazy=True, fontNumber=0)

        tmp_en = td + '_en.otf'
        tmp_zh = td + '_zh.otf'
        en.save(tmp_en)
        new_font.save(tmp_zh)
        en.close()
        new_font.close()

        en = TTFont(tmp_en, lazy=True)
        new_font = TTFont(tmp_zh, lazy=True)

        zh_is_cff = 'CFF ' in new_font
        en_is_cff = 'CFF ' in en

        for tag in ['vhea', 'vmtx', 'VDMX']:
            if tag in new_font:
                del new_font[tag]

        en_glyph_order = en.getGlyphOrder()

        try:
            zh_hmtx = new_font['hmtx']
        except:
            from fontTools.ttLib.tables._h_m_t_x import table__h_m_t_x
            zh_hmtx = table__h_m_t_x()
            zh_hmtx.metrics = {}
            new_font['hmtx'] = zh_hmtx

        for glyph_name in en_glyph_order:
            try:
                metric = en['hmtx'].metrics[glyph_name]
            except:
                metric = (0, 0)
            zh_hmtx.metrics[glyph_name] = metric

        en_is_cff = 'CFF ' in en

        if en_is_ttc:
            pass
        elif zh_is_cff or en_is_cff:
            if zh_is_cff:
                cff_table = new_font['CFF ']
                cff = cff_table.cff
                charstrings = cff.topDictIndex[0].CharStrings
                new_font['maxp'].numGlyphs = min(len(charstrings), 65535)
            else:
                new_font['maxp'].numGlyphs = len(new_font['glyf'].glyphs)
        else:
            en_cmap = en['cmap'].getBestCmap()
            ascii_glyphs = set()
            for cp, glyph_name in en_cmap.items():
                if cp < 0x100:
                    ascii_glyphs.add(glyph_name)

            for g in ascii_glyphs:
                if g in en['glyf'].glyphs and g not in new_font['glyf'].glyphs:
                    new_font['glyf'].glyphs[g] = deepcopy(en['glyf'].glyphs[g])
                    if g not in new_font['glyf'].glyphOrder:
                        new_font['glyf'].glyphOrder.append(g)

            new_font['maxp'].numGlyphs = len(new_font['glyf'].glyphs)

        en_cmap = en['cmap'].getBestCmap()
        en_is_cff = 'CFF ' in en
        zh_glyph_order = new_font.getGlyphOrder()

        if zh_is_cff or en_is_ttc:
            for cmap in new_font['cmap'].tables:
                for cp in list(cmap.cmap.keys()):
                    if cp in en_cmap and cp < 0x100:
                        en_glyph = en_cmap[cp]
                        if en_glyph in zh_glyph_order:
                            cmap.cmap[cp] = en_glyph
        elif en_is_cff:
            pass
        else:
            zh_glyphs = set(new_font['glyf'].glyphs.keys())
            valid_en_glyphs = [g for g in en_glyph_order if g in zh_glyphs]
            all_glyphs = list(set(valid_en_glyphs + zh_glyph_order))
            new_font.setGlyphOrder(all_glyphs)
            new_font['hhea'].numberOfHMetrics = len(all_glyphs)
            new_font['maxp'].numGlyphs = len(all_glyphs)

            for cmap in new_font['cmap'].tables:
                for cp in list(cmap.cmap.keys()):
                    if cp in en_cmap and cp < 0x100:
                        en_glyph = en_cmap[cp]
                        if en_glyph in zh_glyphs:
                            cmap.cmap[cp] = en_glyph

        for r in new_font['name'].names:
            if r.nameID == 1:
                r.string = output_name.encode('utf-16-be')
            elif r.nameID == 4:
                r.string = (output_name + ' Regular').encode('utf-16-be')

        otf = os.path.join(output_dir, f"{output_name}.otf")
        new_font.save(otf)

    finally:
        shutil.rmtree(td, ignore_errors=True)


def merge(
    config,
    font_paths: dict[str, str],
    combinations: list[tuple[str, str]] | None = None,
    force: bool = False,
    manifest=None,
):
    """合并字体，支持增量构建"""
    os.makedirs(config.output_dir, exist_ok=True)

    # 确定要合并的组合
    if combinations is None:
        combinations = [
            (zh.name, en.name)
            for zh in config.all_chinese
            for en in config.all_english
        ]

    # 过滤需要重建的组合
    to_build = []
    for zh_name, en_name in combinations:
        key = f"{zh_name}+{en_name}"
        output_path = os.path.join(config.output_dir, f"{key}.otf")

        if force:
            to_build.append((zh_name, en_name, output_path))
            continue

        # 检查是否需要重建
        zh_path = font_paths.get(zh_name)
        en_path = font_paths.get(en_name)

        if not zh_path or not en_path:
            print(f"  Skipping {key}: source font not found")
            continue

        need_build = False

        if not os.path.exists(output_path):
            need_build = True
        elif manifest:
            # 检查源是否变化
            zh_changed = manifest.check_source_changed(zh_name, zh_path)
            en_changed = manifest.check_source_changed(en_name, en_path)
            if zh_changed or en_changed:
                need_build = True

        if need_build:
            to_build.append((zh_name, en_name, output_path))

    total = len(to_build)
    if total == 0:
        print("\n" + "=" * 60)
        print("Merge: Nothing to build (all up to date)")
        print("=" * 60)
        return

    print("\n" + "=" * 60)
    print(f"Phase 2: Merge ({total} combinations to build, {MAX_WORKERS} workers)")
    print("=" * 60)

    completed = 0
    errors = 0

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for zh_name, en_name, output_path in to_build:
            output_name = f"{zh_name}+{en_name}"
            zh_path = font_paths[zh_name]
            en_path = font_paths[en_name]
            future = executor.submit(merge_single, en_path, zh_path, 0, output_name, config.output_dir)
            futures[future] = output_name

        for future in as_completed(futures):
            completed += 1
            output_name = futures[future]
            try:
                future.result()
                if manifest:
                    zh_name, en_name = output_name.split('+', 1)
                    manifest.mark_clean(zh_name, en_name, os.path.join(config.output_dir, f"{output_name}.otf"))
                print(f"[{completed}/{total}] {output_name} done")
            except Exception as e:
                errors += 1
                print(f"[{completed}/{total}] {output_name} ERROR: {e}")

    print("\n" + "=" * 60)
    print(f"Merge Complete! ({total - errors} ok, {errors} errors)")
    print("=" * 60)

    if errors > 0:
        raise RuntimeError(f"{errors} combinations failed")


def list_outputs(config) -> list[str]:
    """列出所有输出文件"""
    if not os.path.exists(config.output_dir):
        return []
    return sorted([f for f in os.listdir(config.output_dir) if f.endswith('.otf')])
