#!/usr/bin/env python3
"""Manifest 驱动增量构建"""
import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path


@dataclass
class SourceEntry:
    path: str
    mtime: float
    size: int
    status: str = "ok"  # ok, error, missing


@dataclass
class OutputEntry:
    zh: str
    en: str
    path: str
    mtime: float = 0
    dirty: bool = True
    status: str = "pending"  # pending, building, ok, error


@dataclass
class Manifest:
    version: str = "1.0"
    updated: float = 0
    sources: dict[str, SourceEntry] = field(default_factory=dict)
    outputs: dict[str, OutputEntry] = field(default_factory=dict)

    @staticmethod
    def _get_file_info(path: str) -> tuple[float, int] | None:
        try:
            stat = os.stat(path)
            return stat.st_mtime, stat.st_size
        except OSError:
            return None

    def get_source_key(self, zh: str, en: str) -> str:
        return f"{zh}+{en}"

    def check_source_changed(self, name: str, path: str) -> bool:
        """检查源字体是否发生变化"""
        info = self._get_file_info(path)
        if name not in self.sources:
            return True

        source = self.sources[name]
        if info is None:
            return True

        # mtime 或 size 变化则认为改变
        return abs(source.mtime - info[0]) > 0.1 or source.size != info[0]

    def update_source(self, name: str, path: str):
        """更新源字体信息"""
        info = self._get_file_info(path)
        if info:
            self.sources[name] = SourceEntry(path=path, mtime=info[0], size=info[1])

    def mark_dirty(self, zh: str, en: str):
        """标记某个组合需要重建"""
        key = self.get_source_key(zh, en)
        if key in self.outputs:
            self.outputs[key].dirty = True
            self.outputs[key].status = "pending"

    def mark_clean(self, zh: str, en: str, path: str):
        """标记某个组合已构建"""
        key = self.get_source_key(zh, en)
        info = self._get_file_info(path)
        if info:
            self.outputs[key] = OutputEntry(
                zh=zh, en=en, path=path, mtime=info[0], dirty=False, status="ok"
            )

    def get_dirty_outputs(self) -> list[tuple[str, str]]:
        """返回所有需要重建的组合"""
        result = []
        for key, entry in self.outputs.items():
            if entry.dirty:
                result.append((entry.zh, entry.en))
        return result

    def save(self, path: str):
        """保存 manifest"""
        self.updated = time.time()
        data = {
            'version': self.version,
            'updated': self.updated,
            'sources': {k: asdict(v) for k, v in self.sources.items()},
            'outputs': {k: asdict(v) for k, v in self.outputs.items()},
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> 'Manifest':
        """加载 manifest，如果不存在返回空的"""
        if not os.path.exists(path):
            return cls()

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            manifest = cls()
            manifest.version = data.get('version', '1.0')
            manifest.updated = data.get('updated', 0)

            for name, src in data.get('sources', {}).items():
                manifest.sources[name] = SourceEntry(**src)

            for key, out in data.get('outputs', {}).items():
                manifest.outputs[key] = OutputEntry(**out)

            return manifest
        except (json.JSONDecodeError, KeyError, TypeError):
            # manifest 损坏，返回空的
            return cls()

    def init_outputs(self, combinations: list[tuple[str, str]], output_dir: str):
        """初始化所有可能的输出组合"""
        for zh, en in combinations:
            key = self.get_source_key(zh, en)
            if key not in self.outputs:
                path = os.path.join(output_dir, f"{key}.otf")
                self.outputs[key] = OutputEntry(zh=zh, en=en, path=path, dirty=True)
