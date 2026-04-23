#!/usr/bin/env python3
"""Phase 3: 安装字体到系统"""
import os
import subprocess
import shutil


FONT_REGISTRY_PATH = r'HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts'


def get_font_name_display(f: str) -> str:
    """获取字体注册表显示名称"""
    return f.replace('.otf', ' (OpenType)').replace('.ttf', ' (TrueType)')


def get_user_fonts_dir() -> str:
    return os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'Fonts')


def install_font(src_path: str, target_dir: str) -> bool:
    """安装单个字体文件"""
    try:
        shutil.copy2(src_path, target_dir)
        return True
    except Exception as e:
        print(f"    Copy failed: {e}")
        return False


def register_font(font_name: str, font_path: str) -> bool:
    """注册字体到 Windows 注册表"""
    try:
        subprocess.run(
            ['powershell', '-Command',
             f"Set-ItemProperty -Path '{FONT_REGISTRY_PATH}' -Name '{font_name}' -Value '{font_path}'"],
            capture_output=True, timeout=10
        )
        return True
    except Exception as e:
        print(f"    Registry failed: {e}")
        return False


def unregister_font(font_name: str) -> bool:
    """从 Windows 注册表移除字体"""
    try:
        subprocess.run(
            ['powershell', '-Command',
             f"Remove-ItemProperty -Path '{FONT_REGISTRY_PATH}' -Name '{font_name}' -ErrorAction SilentlyContinue"],
            capture_output=True, timeout=10
        )
        return True
    except Exception as e:
        print(f"    Unregister failed: {e}")
        return False


def install(config, names: list[str] | None = None, output_dir: str | None = None):
    """安装字体"""
    if output_dir is None:
        output_dir = config.output_dir

    print("\n" + "=" * 60)
    print("Phase 3: Install")
    print("=" * 60)

    if not os.path.exists(output_dir):
        print(f"  Output directory '{output_dir}' not found")
        return

    files = [f for f in os.listdir(output_dir) if f.endswith('.otf') or f.endswith('.ttf')]
    if not files:
        print(f"  No font files found in '{output_dir}'")
        return

    # 过滤指定名称
    if names:
        # 支持前缀匹配
        filtered = []
        for f in files:
            base = f.replace('.otf', '').replace('.ttf', '')
            for name in names:
                if name in base or base in name:
                    filtered.append(f)
                    break
        files = filtered

    if not files:
        print(f"  No matching font files found")
        return

    print(f"  Found {len(files)} font file(s) to install")

    target_dir = get_user_fonts_dir()
    os.makedirs(target_dir, exist_ok=True)

    installed = 0
    for f in files:
        src = os.path.join(output_dir, f)
        dst = os.path.join(target_dir, f)
        font_name = get_font_name_display(f)

        if install_font(src, target_dir):
            if register_font(font_name, dst):
                print(f"  Installed: {f}")
                installed += 1
            else:
                print(f"  Registered failed: {f}")
        else:
            print(f"  Copy failed: {f}")

    print(f"\n  {installed}/{len(files)} font(s) installed to {target_dir}")
    if installed > 0:
        print(f"  Note: Logout/login may be required for full effect")


def uninstall(config, names: list[str] | None = None, output_dir: str | None = None):
    """卸载字体"""
    if output_dir is None:
        output_dir = config.output_dir

    print("\n" + "=" * 60)
    print("Phase 4: Uninstall")
    print("=" * 60)

    if not os.path.exists(output_dir):
        print(f"  Output directory '{output_dir}' not found")
        return

    files = [f for f in os.listdir(output_dir) if f.endswith('.otf') or f.endswith('.ttf')]
    if not files:
        print(f"  No font files found in '{output_dir}'")
        return

    # 过滤指定名称
    if names:
        filtered = []
        for f in files:
            base = f.replace('.otf', '').replace('.ttf', '')
            for name in names:
                if name in base or base in name:
                    filtered.append(f)
                    break
        files = filtered

    if not files:
        print(f"  No matching font files found")
        return

    print(f"  Found {len(files)} font file(s) to uninstall")

    user_fonts = get_user_fonts_dir()

    uninstalled = 0
    for f in files:
        font_name = get_font_name_display(f)
        font_path = os.path.join(user_fonts, f)

        unregister_font(font_name)

        if os.path.exists(font_path):
            try:
                os.remove(font_path)
            except Exception as e:
                print(f"    Delete failed: {f} - {e}")

        print(f"  Uninstalled: {f}")
        uninstalled += 1

    print(f"\n  {uninstalled} font(s) uninstalled from {user_fonts}")
    if uninstalled > 0:
        print(f"  Note: Restart applications for changes to take effect")


def clean(config, output_dir: str | None = None):
    """清理输出目录"""
    if output_dir is None:
        output_dir = config.output_dir

    print("\n" + "=" * 60)
    print("Clean")
    print("=" * 60)

    if not os.path.exists(output_dir):
        print(f"  Output directory '{output_dir}' not found")
        return

    files = [f for f in os.listdir(output_dir) if f.endswith('.otf') or f.endswith('.ttf')]
    if not files:
        print(f"  No font files to clean")
        return

    print(f"  Found {len(files)} file(s) to clean")
    for f in files:
        path = os.path.join(output_dir, f)
        os.remove(path)
        print(f"  Removed: {f}")

    print(f"\n  {len(files)} file(s) cleaned")
