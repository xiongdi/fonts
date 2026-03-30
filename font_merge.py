#!/usr/bin/env python3
"""字体合并脚本 - 自动生成所有组合"""
import tomllib
import os, subprocess, tempfile, shutil
import zipfile
import httpx
from fontTools.ttLib import TTFont
from copy import deepcopy


def format_size(path: str) -> float:
    """返回文件大小（KB）"""
    return os.path.getsize(path) / 1024


def load_config():
    """从 pyproject.toml 加载配置"""
    with open('pyproject.toml', 'rb') as f:
        return tomllib.load(f)['tool']['font-merge']


def is_url(path: str) -> bool:
    """检查是否为远程 URL"""
    return path.startswith('http://') or path.startswith('https://')


def get_font_name_from_url(url: str) -> str:
    """从 URL 提取字体名称"""
    # 常见等宽字体映射
    name_map = {
        'JetBrainsMono': 'JetBrains Mono',
        'FiraCode': 'Fira Code',
        'SourceCodePro': 'Source Code Pro',
        'RobotoMono': 'Roboto Mono',
        'IBMPlexMono': 'IBM Plex Mono',
    }
    for key, name in name_map.items():
        if key in url:
            return name
    return None


def download_and_extract(url: str, cache_dir: str) -> str | None:
    """下载远程字体 ZIP 并返回 TTF 路径"""
    os.makedirs(cache_dir, exist_ok=True)

    # 从 URL 生成缓存文件名
    filename = url.split('/')[-1].split('?')[0]
    cached_zip = os.path.join(cache_dir, filename)

    # 下载
    if not os.path.exists(cached_zip):
        print(f"  Downloading: {filename}...")
        try:
            with httpx.stream('GET', url, follow_redirects=True) as r:
                r.raise_for_status()
                with open(cached_zip, 'wb') as f:
                    for chunk in r.iter_bytes(chunk_size=8192):
                        f.write(chunk)
        except Exception as e:
            print(f"  Download failed: {e}")
            return None

    # 解压
    extract_dir = cached_zip.replace('.zip', '')
    if not os.path.exists(extract_dir):
        print(f"  Extracting...")
        try:
            with zipfile.ZipFile(cached_zip, 'r') as zf:
                zf.extractall(extract_dir)
        except Exception as e:
            print(f"  Extract failed: {e}")
            return None

    # 查找 TTF 文件
    font_name = get_font_name_from_url(url)
    for root, dirs, files in os.walk(extract_dir):
        for f in files:
            if f.endswith('.ttf') or f.endswith('.otf'):
                # 如果知道字体名，匹配它
                if font_name and font_name not in f:
                    continue
                font_path = os.path.join(root, f)
                # 优先选择 Regular 字体
                if 'Regular' in f or '-Regular' in f:
                    return font_path
                # 如果没有找到指定字体，返回第一个
                if not font_name:
                    return font_path
    # 如果没匹配到，返回第一个
    for root, dirs, files in os.walk(extract_dir):
        for f in files:
            if f.endswith('.ttf') or f.endswith('.otf'):
                return os.path.join(root, f)

    return None


def resolve_font_path(path: str, cache_dir: str) -> str | None:
    """解析字体路径（本地或远程）"""
    if is_url(path):
        return download_and_extract(path, cache_dir)
    elif os.path.exists(path):
        return path
    else:
        return None


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
    cache_dir = config.get('cache-dir', 'cache')

    print("=" * 60)
    print("Font Merge Tool - Generate All Combinations")
    print("=" * 60)

    os.makedirs(output_dir, exist_ok=True)

    # 解析中文字体路径（只需解析一次）
    print("\nResolving Chinese fonts...")
    resolved_zh = []
    for zh in chinese_fonts:
        path = resolve_font_path(zh['path'], cache_dir)
        if path:
            resolved_zh.append({**zh, 'resolved_path': path})
            print(f"  {zh['name']}: {path}")
        else:
            print(f"  {zh['name']}: FAILED")

    # 解析英文字体路径
    print("\nResolving English fonts...")
    resolved_en = []
    for en in english_fonts:
        path = resolve_font_path(en['path'], cache_dir)
        if path:
            resolved_en.append({**en, 'resolved_path': path})
            print(f"  {en['name']}: {os.path.basename(path)}")
        else:
            print(f"  {en['name']}: FAILED")

    total = len(resolved_zh) * len(resolved_en)
    current = 0

    for zh in resolved_zh:
        for en in resolved_en:
            current += 1
            output_name = f"{zh['name']}+{en['name']}"
            print(f"\n[{current}/{total}] {output_name}")

            try:
                merge(en['resolved_path'], zh['resolved_path'], zh['index'], output_name, output_dir)
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
