#!/usr/bin/env python3
"""字体合并脚本 - 自动生成所有组合"""
import tomllib
import os, subprocess, tempfile, shutil
import zipfile
import py7zr
import httpx
from fontTools.ttLib import TTFont
from fontTools.subset import Options, Subsetter, load_font
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


def find_font_in_cache(cache_dir: str, font_name: str) -> str | None:
    """在缓存目录中查找字体文件"""
    # 1. 直接检查缓存根目录的 TTF/OTF 文件（精确匹配）
    for ext in ['.ttf', '.otf']:
        direct = os.path.join(cache_dir, f"{font_name}{ext}")
        if os.path.exists(direct):
            return direct
        direct = os.path.join(cache_dir, f"{font_name}-Regular{ext}")
        if os.path.exists(direct):
            return direct

    # 2. 查找解压后的目录
    for item in os.listdir(cache_dir):
        item_path = os.path.join(cache_dir, item)
        if not os.path.isdir(item_path):
            # 检查是否直接是字体文件（不在子目录中）
            if item.endswith(('.ttf', '.otf', '.ttc')):
                item_clean = item.replace('-', '').replace('_', '').replace('.ttf', '').replace('.otf', '').replace('.ttc', '').lower()
                name_clean = font_name.replace('-', '').replace('_', '').lower()
                if item_clean == name_clean or name_clean in item_clean:
                    return item_path
            continue

        # 目录名去除版本号后匹配
        clean_item = item.replace('-', '').replace('_', '').lower()
        clean_name = font_name.replace('-', '').replace('_', '').lower()

        # 特殊匹配逻辑
        match = False
        if clean_item.startswith(clean_name) or clean_name in clean_item:
            match = True
        # 特殊处理：GeistMono -> geist-font
        if font_name == 'GeistMono' and 'geist' in clean_item:
            match = True
        # 特殊处理：MesloLG -> Meslo
        if font_name == 'MesloLG' and clean_item.startswith('meslo'):
            match = True

        if match:
            # 收集所有匹配的字体文件
            candidates = []

            for root, dirs, files in os.walk(item_path):
                for f in files:
                    if not f.endswith(('.ttf', '.otf', '.ttc')):
                        continue
                    f_lower = f.lower()
                    font_path = os.path.join(root, f)

                    # 优先级：Regular > Normal > 其他
                    if 'regular' in f_lower or '-r.' in f_lower:
                        return font_path  # 直接返回最高优先级
                    elif 'normal' in f_lower:
                        candidates.append((font_path, 1))
                    else:
                        # 计算匹配度
                        f_clean = f_lower.replace(' ', '').replace('-', '').replace('_', '').replace('.ttf', '').replace('.otf', '').replace('.ttc', '')
                        score = len(clean_name) / len(f_clean) if f_clean else 0
                        candidates.append((font_path, score))

            # 返回最佳候选
            if candidates:
                candidates.sort(key=lambda x: x[1], reverse=True)
                return candidates[0][0]

    return None


def get_font_name_from_url(url: str) -> str | None:
    """从 URL 提取字体名称"""
    if 'fonts.google.com' in url:
        import urllib.parse
        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        if 'family' in parsed:
            return parsed['family'][0].replace('%20', ' ')

    if 'github.com' in url:
        # 特殊处理某些字体
        if 'SourceHanSansSC' in url:
            return 'SourceHanSansSC'
        if 'SourceHanSerifSC' in url:
            return 'SourceHanSerifSC'
        if 'Iosevka' in url:
            return 'Iosevka'
        if 'Recursive' in url:
            return 'Recursive'
        if 'Sarasa-Gothic' in url:
            return 'SarasaGothicSC'
        if 'Zhuque' in url or 'zhuque' in url.lower():
            return 'ZhuqueFangsong'
        if 'LxgwWenKai' in url or 'LXGWWenKai' in url:
            return 'LXGWWenKai'
        if 'geist' in url.lower():
            return 'GeistMono'
        if 'intel-one-mono' in url.lower() or 'intel' in url.lower():
            return 'IntelOneMono'
        if 'cozette' in url.lower():
            return 'Cozette'
        if 'meslo' in url.lower():
            return 'MesloLG'

        # 从 URL 提取文件名
        filename = url.split('/')[-1]
        name = filename.replace('.zip', '').replace('.ttf', '').replace('.otf', '').replace('.7z', '').replace('.ttc', '')

        # 移除版本号
        for sep in ['-v', '_v']:
            if sep in name:
                name = name.split(sep)[0]

        # 常见英文字体名称映射
        name_map = {
            'FiraCode': 'FiraCode',
            'CascadiaCode': 'CascadiaCode',
            'MapleMono': 'MapleMono',
            'SourceCodePro': 'SourceCodePro',
            'Monaspace': 'Monaspace',
            'Hack': 'Hack',
            'JetBrainsMono': 'JetBrainsMono',
            'IBMPlexMono': 'IBMPlexMono',
            'Monocraft': 'Monocraft',
            'IntelOneMono': 'IntelOneMono',
            'Monoid': 'Monoid',
            'FantasqueSansMono': 'FantasqueSans',
            'Hasklig': 'Hasklig',
            'Mononoki': 'Mononoki',
            'VictorMono': 'VictorMono',
            'Cozette': 'Cozette',
            'Geist': 'GeistMono',
            'Meslo': 'MesloLG',
        }

        # 清理名称后匹配
        clean = name.replace('-', '').replace('_', '')
        for key, val in name_map.items():
            if key.lower() in clean.lower() or clean.lower() in key.lower():
                return val

        return name

    name_map = {
        'JetBrainsMono': 'JetBrainsMono',
        'FiraCode': 'FiraCode',
        'SourceCodePro': 'SourceCodePro',
        'IBMPlexMono': 'IBMPlexMono',
        'Monaspace': 'Monaspace',
        'Hack': 'Hack',
        'Mononoki': 'Mononoki',
        'JuliaMono': 'JuliaMono',
        'IntelOneMono': 'IntelOneMono',
        'Recursive': 'Recursive',
        'VictorMono': 'VictorMono',
        'SourceHanSansSC': 'SourceHanSansSC',
        'SourceHanSerifSC': 'SourceHanSerifSC',
        'LXGWWenKai': 'LXGWWenKai',
        'ZhuqueFangsong': 'ZhuqueFangsong',
        'SarasaGothicSC': 'SarasaGothicSC',
        'Cozette': 'Cozette',
        'MapleFont': 'MapleFont',
        'Monoid': 'Monoid',
        'FantasqueSans': 'FantasqueSans',
        'Hasklig': 'Hasklig',
        'MesloLG': 'MesloLG',
        'Monocraft': 'Monocraft',
        'GeistMono': 'GeistMono',
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

    # 先检查缓存中是否已有
    if font_name:
        cached = find_font_in_cache(cache_dir, font_name)
        if cached:
            return cached

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


ARCHIVE_EXTENSIONS = {'.zip', '.7z'}


def extract_archive(archive_path: str, font_name: str | None) -> str | None:
    """从压缩包（ZIP/7z）提取字体"""
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


def find_font_file(extract_dir: str, font_name: str | None) -> str | None:
    """在解压目录中查找字体文件"""
    if not font_name:
        return None

    # 清理字体名：移除空格、连字符，转小写
    font_name_clean = font_name.lower().replace(' ', '').replace('-', '').replace('_', '')

    # 优先选择 Regular 版本
    regular_match = None
    # 次选 Normal 版本
    normal_match = None
    # 其他候选
    other_matches = []

    for root, dirs, files in os.walk(extract_dir):
        for f in files:
            if not f.endswith(('.ttf', '.otf', '.ttc')):
                continue

            f_lower = f.lower()
            f_clean = f_lower.replace(' ', '').replace('-', '').replace('_', '').replace('.ttf', '').replace('.otf', '').replace('.ttc', '')

            # 完全匹配（去除扩展名）
            if f_clean == font_name_clean:
                if 'regular' in f_lower or '-r.' in f_lower or f_clean.endswith('regular'):
                    return os.path.join(root, f)
                if 'normal' in f_lower:
                    normal_match = os.path.join(root, f)
                else:
                    other_matches.append(os.path.join(root, f))
            # 部分匹配：字体名必须是文件名的主要部分
            elif font_name_clean in f_clean:
                # 计算匹配度
                score = len(font_name_clean) / len(f_clean)
                if score >= 0.7:  # 至少70%匹配
                    if 'regular' in f_lower or '-r.' in f_lower:
                        regular_match = os.path.join(root, f)
                    elif 'normal' in f_lower:
                        normal_match = os.path.join(root, f)
                    else:
                        other_matches.append((os.path.join(root, f), score))

    # 返回最佳匹配
    if regular_match:
        return regular_match
    if normal_match:
        return normal_match
    if other_matches:
        # 按匹配度排序返回最高的
        other_matches.sort(key=lambda x: x[1] if isinstance(x, tuple) else 0, reverse=True)
        return other_matches[0][0] if isinstance(other_matches[0], tuple) else other_matches[0]
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
    """提取字体 - 直接复制文件（不进行子集化以避免 hhea/hmtx 问题）"""
    import shutil

    font_path = args[0]
    output_path = None

    # 解析参数
    i = 1
    while i < len(args):
        arg = args[i]
        if arg.startswith('--output-file='):
            output_path = arg.split('=', 1)[1]
            break
        elif arg == '--output-file' and i + 1 < len(args):
            output_path = args[i + 1]
            break
        i += 1

    if not output_path:
        raise ValueError(f"No output file specified")

    # 直接复制文件
    shutil.copy2(font_path, output_path)


def has_cff_table(font_path: str) -> bool:
    """检查字体是否使用 CFF 表"""
    try:
        if font_path.endswith('.ttc'):
            # TTC 文件需要指定字体编号
            f = TTFont(font_path, fontNumber=0)
        else:
            f = TTFont(font_path)
        result = 'CFF ' in f
        f.close()
        return result
    except:
        return False


def convert_cff_to_ttf(cff_path: str, output_path: str) -> bool:
    """将 CFF 字体转换为 TTF 格式"""
    try:
        result = subprocess.run(
            ['pyftsubset', cff_path, '--glyphs=*', f'--output-file={output_path}'],
            capture_output=True, timeout=300
        )
        if result.returncode == 0 and os.path.exists(output_path):
            return True
        return False
    except Exception as e:
        print(f"  Convert CFF to TTF failed: {e}")
        return False


def ensure_ttf_font(font_path: str, temp_dir: str) -> str:
    """确保字体是 TTF 格式"""
    if not has_cff_table(font_path):
        return font_path

    # CFF 字体 - 尝试用 pyftsubset 转换
    base_name = os.path.splitext(os.path.basename(font_path))[0]
    ttf_path = os.path.join(temp_dir, f"{base_name}_converted.ttf")

    if os.path.exists(ttf_path):
        return ttf_path

    print(f"  Converting CFF to TTF...")
    try:
        import subprocess
        # 使用 --format=ttf 强制转换为 TTF 格式
        result = subprocess.run(
            ['pyftsubset', font_path, '--glyphs=*', f'--output-file={ttf_path}',
             '--format=ttf', '--ignore-missing-glyphs', '--ignore-missing-unicodes'],
            capture_output=True, timeout=300
        )
        if result.returncode == 0 and os.path.exists(ttf_path):
            # 验证转换结果是否为 TTF
            if not has_cff_table(ttf_path):
                return ttf_path
            else:
                print(f"  Warning: Converted file is still CFF")
    except Exception as e:
        print(f"  Convert failed: {e}")

    print(f"  Warning: CFF conversion failed, using original")
    return font_path


def merge(en_path: str, zh_path: str, zh_index: int, output_name: str, output_dir: str):
    """合并单个字体"""
    print(f"\n{'='*50}")
    print(f"Merge: {os.path.basename(en_path)} + {os.path.basename(zh_path)}")

    td = tempfile.mkdtemp()
    try:
        # 处理 TTC 文件 - 使用第一个字体 (index=0)
        en_is_ttc = en_path.endswith('.ttc')
        zh_is_ttc = zh_path.endswith('.ttc')

        # 检查字体格式
        zh_is_cff = has_cff_table(zh_path) if not zh_is_ttc else False
        en_is_cff = has_cff_table(en_path) if not en_is_ttc else False

        # 对于 CFF 中文字体：尝试转换为 TTF 以支持合并
        if zh_is_cff:
            zh_path_ttf = ensure_ttf_font(zh_path, td)
            if zh_path_ttf != zh_path and os.path.exists(zh_path_ttf):
                zh_path = zh_path_ttf
                zh_is_cff = False  # 转换成功
                print("  Converted CFF to TTF successfully")

        # 对于 CFF 英文字体：同样尝试转换
        if en_is_cff:
            en_path_ttf = ensure_ttf_font(en_path, td)
            if en_path_ttf != en_path and os.path.exists(en_path_ttf):
                en_path = en_path_ttf
                en_is_cff = False  # 转换成功
                print("  Converted English CFF to TTF successfully")

        # 加载原始字体 - 使用 lazy=True 避免立即读取可能有问题的表
        # 对于 TTC 文件，使用 fontNumber=0
        en = TTFont(en_path, lazy=True, fontNumber=0)
        new_font = TTFont(zh_path, lazy=True, fontNumber=0)

        # 保存临时文件
        tmp_en = td + '_en.otf'
        tmp_zh = td + '_zh.otf'
        en.save(tmp_en)
        new_font.save(tmp_zh)
        en.close()
        new_font.close()

        # 重新加载 - 现在表应该被正确编译了
        en = TTFont(tmp_en, lazy=True)
        new_font = TTFont(tmp_zh, lazy=True)

        # 重新检查格式（可能转换后变了）
        zh_is_cff = 'CFF ' in new_font
        en_is_cff = 'CFF ' in en

        # 删除不需要的垂直度量表
        for tag in ['vhea', 'vmtx', 'VDMX']:
            if tag in new_font:
                del new_font[tag]

        # 先添加所有英文字形的 metrics，再修改 glyph order
        en_glyph_order = en.getGlyphOrder()

        # 从中文获取 hmtx 表
        try:
            zh_hmtx = new_font['hmtx']
        except:
            # 如果无法读取，创建一个新的
            from fontTools.ttLib.tables._h_m_t_x import table__h_m_t_x
            zh_hmtx = table__h_m_t_x()
            zh_hmtx.metrics = {}
            new_font['hmtx'] = zh_hmtx

        # 逐个添加英文的字形 metrics - 必须先做这个！
        for glyph_name in en_glyph_order:
            # 尝试从英文字体获取
            try:
                metric = en['hmtx'].metrics[glyph_name]
            except:
                metric = (0, 0)
            zh_hmtx.metrics[glyph_name] = metric

        # 检查英文是否是 CFF（无法直接访问 glyf）
        en_is_cff = 'CFF ' in en

        if zh_is_cff or en_is_cff:
            # 至少有一个是 CFF 字体 - 跳过字形复制
            if zh_is_cff and en_is_cff:
                print("  Warning: Both fonts are CFF, skipping glyph replacement")
            elif zh_is_cff:
                print("  Warning: Chinese font is CFF, skipping glyph replacement")
            else:
                print("  Warning: English font is CFF, skipping glyph replacement")

            # 更新 numGlyphs - CFF 字体最大为 65535
            if zh_is_cff:
                cff_table = new_font['CFF ']
                cff = cff_table.cff
                charstrings = cff.topDictIndex[0].CharStrings
                new_font['maxp'].numGlyphs = min(len(charstrings), 65535)
            else:
                new_font['maxp'].numGlyphs = len(new_font['glyf'].glyphs)
        else:
            # 两个都是 TTF：正常合并
            # 只复制 ASCII 字符 (0x00-0xFF) 对应的字形，避免字形数量超过 65535
            en_cmap = en['cmap'].getBestCmap()
            ascii_glyphs = set()
            for cp, glyph_name in en_cmap.items():
                if cp < 0x100:
                    ascii_glyphs.add(glyph_name)

            print(f"  Adding {len(ascii_glyphs)} ASCII glyphs from English font")

            for g in ascii_glyphs:
                if g in en['glyf'].glyphs and g not in new_font['glyf'].glyphs:
                    new_font['glyf'].glyphs[g] = deepcopy(en['glyf'].glyphs[g])
                    if g not in new_font['glyf'].glyphOrder:
                        new_font['glyf'].glyphOrder.append(g)

            new_font['maxp'].numGlyphs = len(new_font['glyf'].glyphs)

        # 替换 cmap 中的英文字符 - 需要根据字体类型不同处理
        en_cmap = en['cmap'].getBestCmap()
        en_is_cff = 'CFF ' in en
        zh_glyph_order = new_font.getGlyphOrder()

        if zh_is_cff:
            # CFF 字体：只替换 cmap 映射，保持原有 glyph order
            # 注意：英文字符的 glyph name 必须存在于中文字体中
            for cmap in new_font['cmap'].tables:
                for cp in list(cmap.cmap.keys()):
                    if cp in en_cmap and cp < 0x100:
                        en_glyph = en_cmap[cp]
                        if en_glyph in zh_glyph_order:
                            cmap.cmap[cp] = en_glyph
        elif en_is_cff:
            # 中文是 TTF，英文是 CFF：跳过 cmap 替换
            print("  Warning: English font is CFF, cmap not replaced")
        else:
            # 两个都是 TTF：正常处理
            # 检查英文 glyph 是否在中文 glyf 中
            zh_glyphs = set(new_font['glyf'].glyphs.keys())

            # 修复 hhea - 只使用 glyf 中存在的字形
            zh_glyphs = set(new_font['glyf'].glyphs.keys())
            valid_en_glyphs = [g for g in en_glyph_order if g in zh_glyphs]
            all_glyphs = list(set(valid_en_glyphs + zh_glyph_order))
            new_font.setGlyphOrder(all_glyphs)
            new_font['hhea'].numberOfHMetrics = len(all_glyphs)
            new_font['maxp'].numGlyphs = len(all_glyphs)

            # 替换 cmap - 只替换存在的 glyph
            for cmap in new_font['cmap'].tables:
                for cp in list(cmap.cmap.keys()):
                    if cp in en_cmap and cp < 0x100:
                        en_glyph = en_cmap[cp]
                        # 检查 glyph 是否存在于中文字体
                        if en_glyph in zh_glyphs:
                            cmap.cmap[cp] = en_glyph

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
