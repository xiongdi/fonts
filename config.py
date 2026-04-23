#!/usr/bin/env python3
"""配置管理"""
import tomllib
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FontSource:
    name: str
    download: Optional[str] = None
    github: Optional[str] = None
    stars: int = 0
    index: int = 0


@dataclass
class Profile:
    name: str
    chinese: list[str] = field(default_factory=list)
    english: list[str] = field(default_factory=list)


@dataclass
class Config:
    cache_dir: str
    output_dir: str
    profiles: dict[str, Profile] = field(default_factory=dict)
    all_chinese: list[FontSource] = field(default_factory=list)
    all_english: list[FontSource] = field(default_factory=list)


def load_toml(path: str = "pyproject.toml") -> dict:
    with open(path, 'rb') as f:
        return tomllib.load(f)


def get_font_sources(config: dict, key: str) -> list[FontSource]:
    """从配置中提取字体源列表"""
    sources = []
    for item in config.get(key, []):
        sources.append(FontSource(
            name=item['name'],
            download=item.get('download'),
            github=item.get('github'),
            stars=item.get('stars', 0),
            index=item.get('index', 0),
        ))
    return sources


def load_config(toml_path: str = "pyproject.toml") -> Config:
    data = load_toml(toml_path)
    merge_config = data.get('tool', {}).get('font-merge', {})

    cache_dir = merge_config.get('cache-dir', 'fonts/cache')
    output_dir = merge_config.get('output-dir', 'fonts/output')

    all_chinese = get_font_sources(merge_config, 'chinese-fonts')
    all_english = get_font_sources(merge_config, 'english-fonts')

    # 解析 profiles
    profiles = {}
    for profile_name, profile_data in merge_config.get('profiles', {}).items():
        profiles[profile_name] = Profile(
            name=profile_name,
            chinese=profile_data.get('chinese', []),
            english=profile_data.get('english', []),
        )

    # 如果没有 profiles，创建默认的 full profile
    if not profiles:
        profiles['full'] = Profile(
            name='full',
            chinese=[f.name for f in all_chinese],
            english=[f.name for f in all_english],
        )

    return Config(
        cache_dir=cache_dir,
        output_dir=output_dir,
        profiles=profiles,
        all_chinese=all_chinese,
        all_english=all_english,
    )


def get_font_by_name(config: Config, name: str) -> FontSource | None:
    """根据名称查找字体源"""
    for f in config.all_chinese + config.all_english:
        if f.name == name:
            return f
    return None


def resolve_profile(config: Config, profile_name: str | None) -> Profile | None:
    """解析 profile，返回 None 表示使用全部"""
    if not profile_name:
        return None
    return config.profiles.get(profile_name)
