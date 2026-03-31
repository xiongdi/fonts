# Font Merge Tool

字体合并工具 - 将中文字体与英文等宽字体合并，生成适合编程使用的混合字体。

## 功能

- 合并中文字体和英文等宽字体
- 自动下载 GitHub 上的开源字体
- 支持本地字体和远程 URL
- 自动缓存下载的字体

## 使用方法

```bash
python font_merge.py
```

输出文件在 `output/` 目录，下载的字体缓存在 `cache/` 目录。

## 配置

编辑 `pyproject.toml` 中的 `[tool.font-merge]` 部分：

```toml
[tool.font-merge]
chinese-fonts = [
    { name = "LXGWWenKai", github = "https://github.com/lxgw/LxgwWenKai", download = "...", stars = 23700 },
]

english-fonts = [
    { name = "FiraCode", github = "https://github.com/tonsky/FiraCode", download = "...", stars = 81354 },
]

output-dir = "output"
cache-dir = "cache"
```

每个字体支持以下字段：
- `name`: 输出字体名称
- `github`: GitHub 仓库地址
- `download`: 下载链接（ZIP 或 TTF/OTF）
- `stars`: GitHub Stars 数

## 已配置字体

### 中文字体 (5款)

| 字体 | Stars | GitHub |
|------|-------|--------|
| 霞鹜文楷 LXGW WenKai | 23.7k | [lxgw/LxgwWenKai](https://github.com/lxgw/LxgwWenKai) |
| 思源黑体 Source Han Sans | 16.4k | [adobe-fonts/source-han-sans](https://github.com/adobe-fonts/source-han-sans) |
| 得意黑 Smiley Sans | 14.3k | [atelier-anchor/smiley-sans](https://github.com/atelier-anchor/smiley-sans) |
| 思源宋体 Source Han Serif | 9.4k | [adobe-fonts/source-han-serif](https://github.com/adobe-fonts/source-han-serif) |
| Noto CJK | 3.8k | [googlefonts/noto-cjk](https://github.com/googlefonts/noto-cjk) |

### 英文等宽字体 (20款)

| 字体 | Stars | GitHub |
|------|-------|--------|
| Fira Code | 81.4k | [tonsky/FiraCode](https://github.com/tonsky/FiraCode) |
| Cascadia Code | 27.6k | [microsoft/cascadia-code](https://github.com/microsoft/cascadia-code) |
| Maple Font | 24.8k | [subframe7536/maple-font](https://github.com/subframe7536/maple-font) |
| Iosevka | 21.9k | [be5invis/Iosevka](https://github.com/be5invis/Iosevka) |
| Source Code Pro | 20.4k | [adobe-fonts/source-code-pro](https://github.com/adobe-fonts/source-code-pro) |
| Monaspace | 18.7k | [githubnext/monaspace](https://github.com/githubnext/monaspace) |
| Hack | 17.2k | [source-foundry/Hack](https://github.com/source-foundry/Hack) |
| JetBrains Mono | 12.5k | [JetBrains/JetBrainsMono](https://github.com/JetBrains/JetBrainsMono) |
| IBM Plex Mono | 11.3k | [IBM/plex](https://github.com/IBM/plex) |
| Intel One Mono | 9.9k | [intel/intel-one-mono](https://github.com/intel/intel-one-mono) |
| Monoid | 8.0k | [larsenwork/monoid](https://github.com/larsenwork/monoid) |
| Fantasque Sans | 7.3k | [belluzj/fantasque-sans](https://github.com/belluzj/fantasque-sans) |
| Hasklig | 5.8k | [i-tu/Hasklig](https://github.com/i-tu/Hasklig) |
| Mononoki | 4.6k | [madmalik/mononoki](https://github.com/madmalik/mononoki) |
| Cozette | 3.5k | [slavfox/Cozette](https://github.com/slavfox/Cozette) |
| Geist Mono | 3.3k | [vercel/geist-font](https://github.com/vercel/geist-font) |
| Meslo LG | 2.7k | [andreberg/Meslo-Font](https://github.com/andreberg/Meslo-Font) |
| Evil Martians Mono | 2.7k | [evilmartians/mono](https://github.com/evilmartians/mono) |
| JuliaMono | 1.6k | [cormullion/juliamono](https://github.com/cormullion/juliamono) |
| Inconsolata | 1.5k | [googlefonts/Inconsolata](https://github.com/googlefonts/Inconsolata) |

## 依赖

- Python 3.14+
- fonttools
- httpx

## 安装依赖

```bash
pip install fonttools httpx
```

## 原理

1. 下载/读取字体文件
2. 使用 `pyftsubset` 提取字形
3. 以中文字体为基础，添加英文字体字形
4. 替换 ASCII 字符映射 (0x00-0xFF)
5. 删除垂直度量表以确保兼容性
6. 输出 OTF 格式

## 许可证

各字体遵循其原有许可证。
