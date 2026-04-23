#!/usr/bin/env python3
"""Phase 1: 下载字体到缓存目录"""
import os
import zipfile
import py7zr
import httpx
from config import Config, FontSource
from manifest import Manifest


ARCHIVE_EXTENSIONS = {'.zip', '.7z'}


def is_url(path: str) -> bool:
    return path.startswith('http://') or path.startswith('https://')


def get_font_name_from_url(url: str) -> str | None:
    if 'fonts.google.com' in url:
        import urllib.parse
        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        if 'family' in parsed:
            return parsed['family'][0].replace('%20', ' ')

    if 'github.com' in url:
        if 'SourceHanSansSC' in url: return 'SourceHanSansSC'
        if 'SourceHanSerifSC' in url: return 'SourceHanSerifSC'
        if 'Iosevka' in url: return 'Iosevka'
        if 'Recursive' in url: return 'Recursive'
        if 'Sarasa-Gothic' in url: return 'SarasaGothicSC'
        if 'Zhuque' in url or 'zhuque' in url.lower(): return 'ZhuqueFangsong'
        if 'LxgwWenKai' in url or 'LXGWWenKai' in url: return 'LXGWWenKai'
        if 'geist' in url.lower(): return 'GeistMono'
        if 'intel-one-mono' in url.lower() or 'intel' in url.lower(): return 'IntelOneMono'
        if 'cozette' in url.lower(): return 'Cozette'
        if 'meslo' in url.lower(): return 'MesloLG'

        filename = url.split('/')[-1]
        name = filename.replace('.zip', '').replace('.ttf', '').replace('.otf', '').replace('.7z', '').replace('.ttc', '')
        for sep in ['-v', '_v']:
            if sep in name:
                name = name.split(sep)[0]

        name_map = {
            'FiraCode': 'FiraCode', 'CascadiaCode': 'CascadiaCode', 'MapleMono': 'MapleMono',
            'SourceCodePro': 'SourceCodePro', 'Monaspace': 'Monaspace', 'Hack': 'Hack',
            'JetBrainsMono': 'JetBrainsMono', 'IBMPlexMono': 'IBMPlexMono', 'Monocraft': 'Monocraft',
            'IntelOneMono': 'IntelOneMono', 'Monoid': 'Monoid', 'FantasqueSansMono': 'FantasqueSans',
            'Hasklig': 'Hasklig', 'Mononoki': 'Mononoki', 'VictorMono': 'VictorMono',
            'Cozette': 'Cozette', 'Geist': 'GeistMono', 'Meslo': 'MesloLG',
        }
        clean = name.replace('-', '').replace('_', '')
        for key, val in name_map.items():
            if key.lower() in clean.lower() or clean.lower() in key.lower():
                return val
        return name

    name_map = {
        'JetBrainsMono': 'JetBrainsMono', 'FiraCode': 'FiraCode', 'SourceCodePro': 'SourceCodePro',
        'IBMPlexMono': 'IBMPlexMono', 'Monaspace': 'Monaspace', 'Hack': 'Hack',
        'Mononoki': 'Mononoki', 'IntelOneMono': 'IntelOneMono', 'Recursive': 'Recursive',
        'VictorMono': 'VictorMono', 'SourceHanSansSC': 'SourceHanSansSC', 'SourceHanSerifSC': 'SourceHanSerifSC',
        'LXGWWenKai': 'LXGWWenKai', 'ZhuqueFangsong': 'ZhuqueFangsong', 'SarasaGothicSC': 'SarasaGothicSC',
        'Cozette': 'Cozette', 'MapleFont': 'MapleFont', 'Monoid': 'Monoid',
        'FantasqueSans': 'FantasqueSans', 'Hasklig': 'Hasklig', 'MesloLG': 'MesloLG',
        'Monocraft': 'Monocraft', 'GeistMono': 'GeistMono',
    }
    for key, name in name_map.items():
        if key.lower() in url.lower():
            return name
    return None


def find_font_in_cache(cache_dir: str, font_name: str) -> str | None:
    for ext in ['.ttf', '.otf']:
        direct = os.path.join(cache_dir, f"{font_name}{ext}")
        if os.path.exists(direct):
            return direct
        direct = os.path.join(cache_dir, f"{font_name}-Regular{ext}")
        if os.path.exists(direct):
            return direct

    for item in os.listdir(cache_dir):
        item_path = os.path.join(cache_dir, item)
        if not os.path.isdir(item_path):
            if item.endswith(('.ttf', '.otf', '.ttc')):
                item_clean = item.replace('-', '').replace('_', '').replace('.ttf', '').replace('.otf', '').replace('.ttc', '').lower()
                name_clean = font_name.replace('-', '').replace('_', '').lower()
                if item_clean == name_clean or name_clean in item_clean:
                    return item_path
            continue

        clean_item = item.replace('-', '').replace('_', '').lower()
        clean_name = font_name.replace('-', '').replace('_', '').lower()

        match = False
        if clean_item.startswith(clean_name) or clean_name in clean_item:
            match = True
        if font_name == 'GeistMono' and 'geist' in clean_item:
            match = True
        if font_name == 'MesloLG' and clean_item.startswith('meslo'):
            match = True

        if match:
            candidates = []
            for root, dirs, files in os.walk(item_path):
                for f in files:
                    if not f.endswith(('.ttf', '.otf', '.ttc')):
                        continue
                    f_lower = f.lower()
                    font_path = os.path.join(root, f)
                    if 'regular' in f_lower or '-r.' in f_lower:
                        return font_path
                    elif 'normal' in f_lower:
                        candidates.append((font_path, 1))
                    else:
                        f_clean = f_lower.replace(' ', '').replace('-', '').replace('_', '').replace('.ttf', '').replace('.otf', '').replace('.ttc', '')
                        score = len(clean_name) / len(f_clean) if f_clean else 0
                        candidates.append((font_path, score))

            if candidates:
                candidates.sort(key=lambda x: x[1], reverse=True)
                return candidates[0][0]

    return None


def find_font_file(extract_dir: str, font_name: str | None) -> str | None:
    if not font_name:
        return None

    font_name_clean = font_name.lower().replace(' ', '').replace('-', '').replace('_', '')
    regular_match = None
    normal_match = None
    other_matches = []

    for root, dirs, files in os.walk(extract_dir):
        for f in files:
            if not f.endswith(('.ttf', '.otf', '.ttc')):
                continue
            f_lower = f.lower()
            f_clean = f_lower.replace(' ', '').replace('-', '').replace('_', '').replace('.ttf', '').replace('.otf', '').replace('.ttc', '')

            if f_clean == font_name_clean:
                if 'regular' in f_lower or '-r.' in f_lower or f_clean.endswith('regular'):
                    return os.path.join(root, f)
                if 'normal' in f_lower:
                    normal_match = os.path.join(root, f)
                else:
                    other_matches.append(os.path.join(root, f))
            elif font_name_clean in f_clean:
                score = len(font_name_clean) / len(f_clean)
                if score >= 0.7:
                    if 'regular' in f_lower or '-r.' in f_lower:
                        regular_match = os.path.join(root, f)
                    elif 'normal' in f_lower:
                        normal_match = os.path.join(root, f)
                    else:
                        other_matches.append((os.path.join(root, f), score))

    if regular_match:
        return regular_match
    if normal_match:
        return normal_match
    if other_matches:
        other_matches.sort(key=lambda x: x[1] if isinstance(x, tuple) else 0, reverse=True)
        return other_matches[0][0] if isinstance(other_matches[0], tuple) else other_matches[0]
    return None


def extract_archive(archive_path: str, font_name: str | None) -> str | None:
    from pathlib import Path
    ext = Path(archive_path).suffix.lower()
    extract_dir = archive_path[:-len(ext)] if ext in ARCHIVE_EXTENSIONS else archive_path

    if not os.path.exists(extract_dir):
        print(f"  Extracting {ext or 'archive'}...")
        try:
            if ext == '.7z':
                with py7zr.SevenZipFile(archive_path, 'r') as szf:
                    szf.extractall(extract_dir)
            else:
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    zf.extractall(extract_dir)
        except Exception as e:
            print(f"  Extract failed: {e}")
            return None

    return find_font_file(extract_dir, font_name)


def download_single(url: str, cache_dir: str) -> str | None:
    os.makedirs(cache_dir, exist_ok=True)
    font_name = get_font_name_from_url(url)

    if not font_name and 'fonts.gstatic.com/s/' in url:
        match = url.split('fonts.gstatic.com/s/')[1].split('/')[0] if 'fonts.gstatic.com/s/' in url else None
        if match:
            font_name = match.replace('-', ' ').title().replace(' ', '')

    if font_name:
        cached = find_font_in_cache(cache_dir, font_name)
        if cached:
            return cached

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

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


def download(config: Config, names: list[str] | None = None, manifest: Manifest | None = None) -> dict[str, str]:
    os.makedirs(config.cache_dir, exist_ok=True)

    print("\n" + "=" * 60)
    print("Phase 1: Download")
    print("=" * 60)

    results = {}

    if names:
        targets = [f for f in config.all_chinese + config.all_english if f.name in names]
    else:
        targets = config.all_chinese + config.all_english

    for font in targets:
        url = font.download
        if not url:
            if os.path.exists(font.name):
                results[font.name] = font.name
                continue
            print(f"  {font.name}: No download URL")
            continue

        if not is_url(url):
            if os.path.exists(url):
                results[font.name] = url
                if manifest:
                    manifest.update_source(font.name, url)
            else:
                print(f"  {font.name}: File not found: {url}")
            continue

        path = download_single(url, config.cache_dir)
        if path:
            results[font.name] = path
            if manifest:
                manifest.update_source(font.name, path)
            print(f"  {font.name}: {os.path.basename(path)}")
        else:
            print(f"  {font.name}: FAILED")

    return results
