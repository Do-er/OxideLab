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
  - 底板：`x="88" y="88" width="848" height="848" rx="192"`
  - 主图形比例：按实际包围盒居中缩放到圆角底板的 **65%**（约 `551 px`）
- 渲染工具：macOS 上使用 `AppKit / CoreSVG`（禁止使用 `qlmanage`，否则四角会被填充不透明白底），再用 `iconutil` 生成 `icon.icns`、`sips` 生成各尺寸 PNG 及多分辨率 `.ico`。

## 2. 颜色色板（Palette）

| 颜色键 | 十六进制色号 | 说明 |
| :--- | :--- | :--- |
| `orange` | `#EA580C` | 默认主色（与默认主题 `ui.accent` 一致的 Rust 铜橙） |
| `blue` | `#2B82F6` | 亮蓝色 |
| `graphite` | `#121316` | 深邃矿物黑曜石 |
| `green` | `#16A34A` | 翠绿色 |
| `purple` | `#7C3AED` | 紫罗兰 |
| `pink` | `#F472B6` | 甜美桃粉（对应原 `WhiteRed` / `FilledRed` 枚举位） |

- 浅色底板（`default` 及 `white-*`）：底色 `#FBFBFD`，描边 `#E5E7EB`（`stroke-width="4"`），前景图形使用上表对应颜色。
- 实色底板（`filled-*`）：底色使用上表对应颜色（无描边），前景图形使用 `#FFFFFF`。

## 3. 12 套变体与代码映射

枚举 `AppIconVariant` 保留 `WhiteRed` / `FilledRed` 以兼容已有 `settings.json`，资源文件统一命名为 `white-pink.{png,ico}` 与 `filled-pink.{png,ico}`，映射位于 `crates/oxideterm-gpui-app/src/app_icon.rs`：

- `Default` → `default.png` / `default.ico`（同时作为 `icon.png`、`icon.ico`、`icon.icns` 与多尺寸 PNG 源）
- `WhiteBlue` → `white-blue.{png,ico}`
- `WhiteGraphite` → `white-graphite.{png,ico}`
- `WhiteGreen` → `white-green.{png,ico}`
- `WhitePurple` → `white-purple.{png,ico}`
- `WhiteRed` → `white-pink.{png,ico}`
- `FilledOrange` → `filled-orange.{png,ico}`
- `FilledBlue` → `filled-blue.{png,ico}`
- `FilledGraphite` → `filled-graphite.{png,ico}`
- `FilledGreen` → `filled-green.{png,ico}`
- `FilledPurple` → `filled-purple.{png,ico}`
- `FilledRed` → `filled-pink.{png,ico}`
