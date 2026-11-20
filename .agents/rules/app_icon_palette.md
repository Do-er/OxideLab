---
trigger: model_decision
glob:
description: OxideLab 应用图标色板、圆角底板规范与变体文件映射；仅在修改、替换或重新生成应用图标时加载。
---

# OxideLab 应用图标色板与生成规范

## 1. 矢量母版与圆角规范

- 主矢量图形：`crates/oxideterm-gpui-app/resources/icons/oxide-mark.svg`
- 画布与圆角底板（macOS Squircle）：
  - 画布：`1024 × 1024`（透明背景，四角 `alpha = 0`）
  - PNG / ICNS 底板：`x="88" y="88" width="848" height="848" rx="192"`
  - 主图形比例：按实际包围盒居中缩放到圆角底板的 **80%**（`848` 底板下约 `677 px`）
  - ICO 底板：`1024` 满幅（`x=y=0`，圆角随底板等比缩放为 `rx≈232`），比例同为 **80%**
  - 全局底板：`generate_icons.py --plate <边长>`（默认 `848`，作用于所有输出）；调大（如 `960` ≈ 94% 覆盖）可整体恢复旧版 Windows 任务栏观感
  - ICO 覆盖：`--ico-plate <边长>` / `--ico-ratio <比例>`（可选，默认继承 `--plate` / `--ratio`，仅影响 `icon.ico` 与 `variants/*.ico`）
  - **当前已提交产物对应的命令**（`--ico-plate` 是必需的，省略会让 Windows 图标缩进一圈）：
    ```bash
    python3 .agents/skills/oxidelab-app-icons/scripts/generate_icons.py \
      --svg crates/oxideterm-gpui-app/resources/icons/oxide-mark.svg \
      --plate 848 --ratio 0.80 --ico-plate 1024 --ico-ratio 0.80
    ```
- 渲染工具：macOS 上使用 `AppKit / CoreSVG`（禁止使用 `qlmanage`，否则四角会被填充不透明白底），再用 `iconutil` 生成 `icon.icns`、`sips` 生成各尺寸 PNG 及多分辨率 `.ico`。Windows/Linux 上使用 `resvg` + `Pillow`：每个 PNG 按目标尺寸直接矢量渲染（无降采样），`.ico`/`.icns` 容器由脚本纯 Python 封装，构图语义与 macOS 路径一致。

## 2. 颜色色板（Palette）

| 颜色键 | 十六进制色号 | 说明 |
| :--- | :--- | :--- |
| `orange` | `#EA580C` | 与默认主题 `ui.accent` 一致的 Rust 铜橙（**`white-orange` 变体使用此色**） |
| `blue` | `#2B82F6` | 亮蓝色 |
| `graphite` | `#121316` | 深邃矿物黑曜石（**`default` 变体使用此色**） |
| `green` | `#16A34A` | 翠绿色 |
| `purple` | `#7C3AED` | 紫罗兰 |
| `pink` | `#F472B6` | 甜美桃粉（对应原 `WhiteRed` / `FilledRed` 枚举位） |

- 浅色底板（`default` 及 `white-*`）：底色 `#FBFBFD`，描边 `#E5E7EB`（`stroke-width="4"`），前景图形使用上表对应颜色。
- 实色底板（`filled-*`）：底色使用上表对应颜色（无描边），前景图形使用 `#FFFFFF`。

## 3. 12 套变体与代码映射

枚举 `AppIconVariant` 保留 `WhiteRed` / `FilledRed` 以兼容已有 `settings.json`，资源文件统一命名为 `white-pink.{png,ico}` 与 `filled-pink.{png,ico}`，映射位于 `crates/oxideterm-gpui-app/src/app_icon.rs`。

`Default` 不只是选择器里的第一格：它就是安装包资源本体（`icon.png`、`icon.ico`、`icon.icns`、Linux 多尺寸 PNG），也就是安装器界面、快捷方式、Dock 与任务栏上看到的图标。因此它在 `icons/` **根目录**，`variants/` 下没有 `default.{png,ico}` 副本，生成器对 `default` 项直接写根目录。它的前景必须留在 `graphite`，不能用橙色强调色。橙色由 `WhiteOrange` 承载。

- `Default` → `icon.png` / `icon.ico`（根目录，同时是 `icon.icns` 与 Linux 多尺寸 PNG 的来源）
- `WhiteOrange` → `variants/white-orange.{png,ico}`
- `WhiteBlue` → `variants/white-blue.{png,ico}`
- `WhiteGreen` → `variants/white-green.{png,ico}`
- `WhitePurple` → `variants/white-purple.{png,ico}`
- `WhiteRed` → `variants/white-pink.{png,ico}`
- `FilledOrange` → `variants/filled-orange.{png,ico}`
- `FilledBlue` → `variants/filled-blue.{png,ico}`
- `FilledGraphite` → `variants/filled-graphite.{png,ico}`
- `FilledGreen` → `variants/filled-green.{png,ico}`
- `FilledPurple` → `variants/filled-purple.{png,ico}`
- `FilledRed` → `variants/filled-pink.{png,ico}`
