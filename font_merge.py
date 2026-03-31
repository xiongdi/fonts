#!/usr/bin/env python3
"""字体合并脚本 - 自动生成所有组合"""
import tomllib
import os, subprocess, tempfile, shutil
import zipfile
import py7zr
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


def get_font_name_from_url(url: str) -> str | None:
    """从 URL 提取字体名称"""
    if 'fonts.google.com' in url:
        import urllib.parse
        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        if 'family' in parsed:
            return parsed['family'][0].replace('%20', ' ')

    if 'github.com' in url:
        filename = url.split('/')[-1]
        name = filename.replace('.zip', '').replace('.ttf', '').replace('.otf', '')
        for sep in ['-', '_v', '-v']:
            if sep in name:
                name = name.split(sep)[0]
        return name

    name_map = {
        'JetBrainsMono': 'JetBrains Mono',
        'FiraCode': 'Fira Code',
        'SourceCodePro': 'Source Code Pro',
        'IBMPlexMono': 'IBM Plex Mono',
        'Monaspace': 'Monaspace',
        'Hack': 'Hack',
        'Mononoki': 'Mononoki',
        'JuliaMono': 'Julia Mono',
        'IntelOneMono': 'Intel One Mono',
        'Recursive': 'Recursive',
        'VictorMono': 'Victor Mono',
        'SourceHanSansSC': 'Source Han Sans SC',
        'SourceHanSerifSC': 'Source Han Serif SC',
        'LXGWWenKai': 'LXGW WenKai',
        'ZhuqueFangsong': 'Zhuque Fangsong',
        'SarasaGothicSC': 'Sarasa Gothic SC',
    }
    for key, name in name_map.items():
        if key.lower() in url.lower():
            return name
    return None


def download_and_extract(url: str, cache_dir: str) -> str | None:
    """下载远程字体 ZIP 并返回 TTF 路径"""
    os.makedirs(cache_dir, exist_ok=True)
    font_name = get_font_name_from_url(url)

    if not font_name and 'fonts.gstatic.com/s/' in url:
        match = url.split('fonts.gstatic.com/s/')[1].split('/')[0] if 'fonts.gstatic.com/s/' in url else None
        if match:
            font_name = match.replace('-', ' ').title().replace(' ', '')

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    if 'fonts.google.com' in url or 'fonts.gstatic.com' in url:
        safe_name = font_name.replace(' ', '_') if font_name else 'font'
        cached_ttf = os.path.join(cache_dir, f"{safe_name}.ttf")

        if not os.path.exists(cached_ttf):
            print(f"  Downloading: {font_name or 'font'}...")
            for attempt in range(3):
                try:
                    with httpx.stream('GET', url, headers=headers, follow_redirects=True, timeout=60.0) as r:
                        r.raise_for_status()
                        content_type = r.headers.get('content-type', '')
                        if 'zip' in content_type:
                            zip_path = cached_ttf.replace('.ttf', '.zip')
                            with open(zip_path, 'wb') as f:
                                for chunk in r.iter_bytes(chunk_size=8192):
                                    f.write(chunk)
                            return extract_archive(zip_path, font_name)
                        else:
                            with open(cached_ttf, 'wb') as f:
                                for chunk in r.iter_bytes(chunk_size=8192):
                                    f.write(chunk)
                            return cached_ttf
                except Exception as e:
                    if attempt < 2:
                        print(f"  Retry {attempt + 1}/3...")
                        continue
                    print(f"  Download failed: {e}")
                    return None
        return cached_ttf

    filename = url.split('/')[-1].split('?')[0]
    cached_zip = os.path.join(cache_dir, filename)

    if not os.path.exists(cached_zip):
        print(f"  Downloading: {filename}...")
        for attempt in range(3):
            try:
                with httpx.stream('GET', url, headers=headers, follow_redirects=True, timeout=60.0) as r:
                    r.raise_for_status()
                    with open(cached_zip, 'wb') as f:
                        for chunk in r.iter_bytes(chunk_size=8192):
                            f.write(chunk)
                    break
            except Exception as e:
                if attempt < 2:
                    print(f"  Retry {attempt + 1}/3...")
                    continue
                print(f"  Download failed: {e}")
                return None

    return extract_archive(cached_zip, font_name)


def extract_archive(archive_path: str, font_name: str | None) -> str | None:
    """从压缩包（ZIP/7z）提取字体"""
    if archive_path.endswith('.7z'):
        return extract_from_7z(archive_path, font_name)
    else:
        return extract_from_zip(archive_path, font_name)


def extract_from_7z(archive_path: str, font_name: str | None) -> str | None:
    """从 7z 文件提取字体"""
    extract_dir = archive_path.replace('.7z', '')
    if not os.path.exists(extract_dir):
        print(f"  Extracting 7z...")
        try:
            with py7zr.SevenZipFile(archive_path, 'r') as szf:
                szf.extractall(extract_dir)
        except Exception as e:
            print(f"  Extract failed: {e}")
            return None

    return find_font_file(extract_dir, font_name)


def extract_from_zip(zip_path: str, font_name: str | None) -> str | None:
    """从 ZIP 文件提取字体"""
    extract_dir = zip_path.replace('.zip', '')
    if not os.path.exists(extract_dir):
        print(f"  Extracting...")
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_dir)
        except Exception as e:
            print(f"  Extract failed: {e}")
            return None

    return find_font_file(extract_dir, font_name)


def find_font_file(extract_dir: str, font_name: str | None) -> str | None:
    """在解压目录中查找字体文件"""
    # First pass: look for Regular, try to match font name (looser matching)
    candidates = []
    for root, dirs, files in os.walk(extract_dir):
        for f in files:
            if f.endswith('.ttf') or f.endswith('.otf'):
                font_path = os.path.join(root, f)
                # Check for regular weight
                is_regular = 'Regular' in f or '-Regular' in f or 'normal' in f.lower()
                # Check if font name matches (if we have one) - looser matching: only check if any part matches
                matches_name = True
                if font_name:
                    # Strip leading numbers like "09_" from Source Han releases
                    font_name_clean = ''.join(c for c in font_name.lower() if c.isalpha())
                    f_clean = ''.join(c for c in f.lower() if c.isalpha())
                    matches_name = font_name_clean in f_clean
                if matches_name:
                    candidates.append((is_regular, font_path))
                    if is_regular:
                        return font_path

    # If we have any candidates, return the first one
    if candidates:
        return candidates[0][1]

    # Fallback: return any font found
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
        if zh_path.endswith('.ttc'):
            run_subset(['pyftsubset', zh_path, f'--font-number={zh_index}', '--glyphs=*', f'--output-file={zh_sub}'])
        else:
            run_subset(['pyftsubset', zh_path, '--glyphs=*', f'--output-file={zh_sub}'])

        # 提取英文字体
        en_sub = os.path.join(td, 'en.ttf')
        run_subset(['pyftsubset', en_path, '--glyphs=*', f'--output-file={en_sub}'])

        en = TTFont(en_sub)
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

        # 替换 cmap 中的英文字符
        en_cmap = en['cmap'].getBestCmap()
        for cmap in new_font['cmap'].tables:
            for cp in cmap.cmap.keys():
                if cp in en_cmap and cp < 0x100:
                    cmap.cmap[cp] = en_cmap[cp]

        new_font['maxp'].numGlyphs = len(new_font['glyf'].glyphs)
        new_font['hhea'].numberOfHMetrics = new_font['maxp'].numGlyphs

        # 设置名称
        for r in new_font['name'].names:
            if r.nameID == 1:
                r.string = output_name.encode('utf-16-be')
            elif r.nameID == 4:
                r.string = (output_name + ' Regular').encode('utf-16-be')

        # 保存
        otf = os.path.join(output_dir, f"{output_name}.otf")
        print(f"Save OTF: {otf}")
        new_font.save(otf)
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

    print("\nResolving Chinese fonts...")
    resolved_zh = []
    for zh in chinese_fonts:
        url = zh.get('download') or zh.get('path', '')
        path = resolve_font_path(url, cache_dir)
        if path:
            resolved_zh.append({**zh, 'resolved_path': path})
            print(f"  {zh['name']}: {os.path.basename(path)}")
        else:
            print(f"  {zh['name']}: FAILED")

    print("\nResolving English fonts...")
    resolved_en = []
    for en in english_fonts:
        url = en.get('download') or en.get('path', '')
        path = resolve_font_path(url, cache_dir)
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
                merge(en['resolved_path'], zh['resolved_path'], zh.get('index', 0), output_name, output_dir)
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
