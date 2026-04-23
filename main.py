#!/usr/bin/env python3
"""字体合并工具 - manifest 驱动增量构建"""
import argparse
import os
import sys

from config import load_config, get_font_by_name
from manifest import Manifest
from downloader import download
from merger import merge, list_outputs
from installer import install, uninstall, clean


MANIFEST_PATH = "fonts/manifest.json"


def cmd_download(args, config, manifest):
    font_paths = download(config, args.font, manifest)
    if manifest:
        manifest.save(MANIFEST_PATH)
    return font_paths


def cmd_build(args, config, manifest, font_paths):
    if args.combination:
        # 指定组合: "LXGWWenKai+FiraCode" 或 "LXGWWenKai FiraCode"
        combos = []
        for c in args.combination:
            if '+' in c:
                zh, en = c.split('+', 1)
            else:
                # 尝试从配置中找
                zh_candidates = [f.name for f in config.all_chinese if f.name.startswith(c)]
                en_candidates = [f.name for f in config.all_english if f.name.startswith(c)]
                if zh_candidates and en_candidates:
                    zh, en = zh_candidates[0], en_candidates[0]
                else:
                    print(f"  Cannot determine combination from: {c}")
                    continue
            combos.append((zh, en))
    elif args.profile:
        profile = config.profiles.get(args.profile)
        if not profile:
            print(f"  Profile '{args.profile}' not found")
            return
        combos = [(zh, en) for zh in profile.chinese for en in profile.english]
    else:
        combos = None  # 构建全部

    try:
        merge(config, font_paths, combos, args.force, manifest)
    except RuntimeError as e:
        print(f"  Build failed: {e}")
        sys.exit(1)

    if manifest:
        manifest.save(MANIFEST_PATH)


def cmd_install(args, config):
    install(config, args.font)


def cmd_uninstall(args, config):
    uninstall(config, args.font)


def cmd_clean(args, config):
    if not args.force:
        confirm = input("  This will delete all output fonts. Continue? [y/N]: ")
        if confirm.lower() != 'y':
            print("  Cancelled")
            return
    clean(config)


def cmd_list(args, config):
    print("\n" + "=" * 60)
    print("Available Fonts")
    print("=" * 60)

    print("\nChinese fonts:")
    for f in config.all_chinese:
        print(f"  {f.name} (stars: {f.stars})")

    print("\nEnglish fonts:")
    for f in config.all_english:
        print(f"  {f.name} (stars: {f.stars})")

    print("\nProfiles:")
    for name, profile in config.profiles.items():
        print(f"  {name}: {len(profile.chinese)} zh x {len(profile.english)} en")

    outputs = list_outputs(config)
    print(f"\nOutput fonts: {len(outputs)}")
    if outputs and not args.verbose:
        print(f"  (use --verbose to see all)")
    elif outputs:
        for o in outputs:
            print(f"  {o}")


def main():
    parser = argparse.ArgumentParser(description='Font Merge Tool')
    sub = parser.add_subparsers(dest='command', required=True)

    # download
    p_download = sub.add_parser('download', help='Download fonts')
    p_download.add_argument('font', nargs='*', help='Font names to download')

    # build
    p_build = sub.add_parser('build', help='Build merged fonts')
    p_build.add_argument('combination', nargs='*', help='Combinations (e.g., LXGWWenKai+FiraCode)')
    p_build.add_argument('--profile', help='Build by profile (e.g., dev, full)')
    p_build.add_argument('--force', action='store_true', help='Force rebuild all')

    # install
    p_install = sub.add_parser('install', help='Install fonts to system')
    p_install.add_argument('font', nargs='*', help='Font names to install')

    # uninstall
    p_uninstall = sub.add_parser('uninstall', help='Uninstall fonts from system')
    p_uninstall.add_argument('font', nargs='*', help='Font names to uninstall')

    # clean
    p_clean = sub.add_parser('clean', help='Clean output directory')
    p_clean.add_argument('--force', action='store_true', help='Skip confirmation')

    # list
    p_list = sub.add_parser('list', help='List available fonts')
    p_list.add_argument('--verbose', action='store_true', help='Show all outputs')

    args = parser.parse_args()

    config = load_config()
    manifest = Manifest.load(MANIFEST_PATH)

    # 确保 fonts 目录存在
    os.makedirs(config.cache_dir, exist_ok=True)
    os.makedirs(config.output_dir, exist_ok=True)

    if args.command == 'download':
        cmd_download(args, config, manifest)
    elif args.command == 'build':
        # build 需要先确保字体已下载
        font_paths = {}
        for f in config.all_chinese + config.all_english:
            path = manifest.sources.get(f.name)
            if path and os.path.exists(path.path):
                font_paths[f.name] = path.path

        if not font_paths:
            font_paths = download(config, None, manifest)
            manifest.save(MANIFEST_PATH)

        cmd_build(args, config, manifest, font_paths)
    elif args.command == 'install':
        cmd_install(args, config)
    elif args.command == 'uninstall':
        cmd_uninstall(args, config)
    elif args.command == 'clean':
        cmd_clean(args, config)
    elif args.command == 'list':
        cmd_list(args, config)


if __name__ == '__main__':
    main()
