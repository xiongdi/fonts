#!/usr/bin/env python3
"""字体合并脚本 - 自动生成所有组合"""
import tomllib
import os, subprocess, tempfile, shutil
from fontTools.ttLib import TTFont
from copy import deepcopy


def format_size(path: str) -> float:
    """返回文件大小（KB）"""
    return os.path.getsize(path) / 1024


def load_config():
    """从 pyproject.toml 加载配置"""
    with open('pyproject.toml', 'rb') as f:
        return tomllib.load(f)['tool']['font-merge']


def run_subset(args: list[str]):
    """运行 pyftsubset"""
    result = subprocess.run(args, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"pyftsubset failed: {result.stderr.decode()}")


def merge(en_path: str, zh_path: str, zh_index: int, output_name: str, output_dir: str):
    """合并单个字体"""
    print(f"\n{'='*50}")
    print(f"Merge: {os.path.basename(en_path)} + {os.path.basename(zh_path)}")

    td = tempfile.mkdtemp()
    try:
        # 提取中文字体
        zh_sub = os.path.join(td, 'zh.ttf')
        run_subset(['pyftsubset', zh_path, f'--font-number={zh_index}', '--glyphs=*',
                    f'--output-file={zh_sub}'])

        # 提取英文字体
        en_sub = os.path.join(td, 'en.ttf')
        run_subset(['pyftsubset', en_path, '--glyphs=*', f'--output-file={en_sub}'])

        en = TTFont(en_sub)

        # 以中文字体为基础
        new_font = TTFont(zh_sub)

        # 删除不需要的垂直度量表
        for tag in ['vhea', 'vmtx', 'VDMX']:
            if tag in new_font:
                del new_font[tag]

        # 添加英文字形
        for g in en['glyf'].glyphs:
            if g not in new_font['glyf'].glyphs:
                new_font['glyf'].glyphs[g] = deepcopy(en['glyf'].glyphs[g])
                new_font['glyf'].glyphOrder.append(g)

        # 添加 hmtx
        for g in en['hmtx'].metrics:
            new_font['hmtx'].metrics[g] = en['hmtx'].metrics[g]

        # 替换 cmap 中的英文字符 (只处理 ASCII 范围)
        en_cmap = en['cmap'].getBestCmap()
        for cmap in new_font['cmap'].tables:
            for cp in cmap.cmap.keys():
                if cp in en_cmap and cp < 0x100:
                    cmap.cmap[cp] = en_cmap[cp]

        new_font['maxp'].numGlyphs = len(new_font['glyf'].glyphs)

        # 更新 hhea
        new_font['hhea'].numberOfHMetrics = new_font['maxp'].numGlyphs

        # 设置名称
        for r in new_font['name'].names:
            if r.nameID == 1:
                r.string = output_name.encode('utf-16-be')
            elif r.nameID == 4:
                r.string = (output_name + ' Regular').encode('utf-16-be')

        # 保存 OTF
        otf = os.path.join(output_dir, f"{output_name}.otf")
        print(f"Save OTF: {otf}")
        new_font.save(otf)

        # 保存 WOFF2
        woff = os.path.join(output_dir, f"{output_name}.woff2")
        print(f"Save WOFF2: {woff}")
        try:
            run_subset(['pyftsubset', otf, '--flavor=woff2', f'--output-file={woff}'])
        except RuntimeError:
            print(f"  (WOFF2 skipped)")

        print(f"Done! ({format_size(otf):.1f} KB)")

    finally:
        shutil.rmtree(td, ignore_errors=True)


def main():
    config = load_config()
    chinese_fonts = config['chinese-fonts']
    english_fonts = config['english-fonts']
    output_dir = config['output-dir']

    print("=" * 60)
    print("Font Merge Tool - Generate All Combinations")
    print("=" * 60)

    os.makedirs(output_dir, exist_ok=True)

    total = len(chinese_fonts) * len(english_fonts)
    current = 0

    for zh in chinese_fonts:
        for en in english_fonts:
            current += 1
            output_name = f"{zh['name']}+{en['name']}"
            print(f"\n[{current}/{total}] {output_name}")

            try:
                merge(en['path'], zh['path'], zh['index'], output_name, output_dir)
            except Exception as e:
                print(f"  Error: {e}")

    print("\n" + "=" * 60)
    print("All Complete!")
    print("=" * 60)

    print("\nOutput files:")
    for f in sorted(os.listdir(output_dir)):
        path = os.path.join(output_dir, f)
        print(f"  {f} ({format_size(path):.1f} KB)")


if __name__ == '__main__':
    main()
