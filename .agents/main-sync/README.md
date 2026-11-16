# main → dev 同步台账

dev 面向调试与嵌入式开发人员，不面向网络运维人员；所有合入判断以此为偏向。

合入规则、水位与领域决策记录在本文件；每次同步梳理在 `.agents/main-sync/` 目录下单独建一个按日期命名的批次文件（见「批次索引」），该批次的提交清单与处置结果只写在批次文件里。

- 基线：`b4e5c653`（dev 从 main 分叉前最后一个 main 提交）
- 已同步水位：`617d889ac`（2026-11-06，止于批次 `2026-11-06.md` 的 #79）
- 清单覆盖至：`e7108be9c`（2026-11-15，origin/main 最新）
- 统计时间：2026-11-15

## 批次索引

| 批次 | 覆盖至 | 提交数 | 状态 |
| --- | --- | --- | --- |
| [`2026-11-06.md`](2026-11-06.md) | `617d889ac` | 79 | 全部处置完毕 |
| [`2026-11-15.md`](2026-11-15.md) | `e7108be9c` | 72 | 梳理中 |

复现命令：

```bash
git log --no-merges <清单覆盖至>..main        # 增量提交清单
git cherry -v dev main                        # ± 对应已合入 / 未合入
git merge-tree --write-tree --merge-base=<提交>^ dev <提交>   # 单提交落到 dev 的冲突预览
```

判定规则：

- 状态 `✅` 表示已处置（含确认不采纳），`⬜` 表示待处置。状态只回答「处理过没有」，与内容是否进入 dev 无关。
- 处置 记录处理方式：`直接继承`（分叉前已在 dev）、`cherry-pick 合入`、`路径对齐`（零分叉路径取 main 终态，多行可共用同一 dev 提交）、`手工移植`、`不同步`、`未处理`。未进入 dev 但已决定不采纳的条目同样是 ✅。
- 计数与枚举类冲突（设置分区数、枚举分支、页码映射）必须先核对 dev 页面的实际结构再裁决：main 的计数反映 main 的页面，dev 的计数反映 dev 的页面，取错一侧会让整个页面不可达（已知案例：#34 的 Privilege 2 vs 3）。

## 文件与维护流程

- 本文件只维护水位、领域决策、判定规则和批次索引，不写提交清单。
- 每次同步梳理在 `.agents/main-sync/` 目录下新建以日期命名的批次文件（如 `2026-11-15.md`；同日第二批加 `-2` 后缀），该批次的提交清单、处置结果、合并提交说明都只写在批次文件里，只追加，不删行。
- 批次文件里的 `#n` 编号只在文件内有效；说明里引用其他批次的条目时写 main 提交哈希。

每次梳理按以下顺序：

1. `git fetch origin main` 后执行 `git log --no-merges <清单覆盖至>..main`，在新建的批次文件里落新提交清单，并更新本文件头部的「清单覆盖至」「统计时间」与「批次索引」（新批次先标「梳理中」）；「已同步水位」只在 dev 实际吸收了 main 内容后才推进。
2. 新提交逐个执行 `git cherry -v dev main`：`-` 表示内容已在 dev，处置按来源填「直接继承」或「cherry-pick 合入」，并写 dev 侧提交；`+` 表示未进入 dev，按下面的领域规则处理。
3. 每条 `+` 先按合入偏向分性质，再判定领域（取值见「领域决策」表），按其决策填 `处置` 并置状态：
   - 合入偏向：按方向契合度判断，不按类别预设结果——方向内的提交照常走领域规则，运维向的填「不同步」并写明理由，拿不准的新功能保留「未处理」与 ⬜ 逐条评估。
   - 领域决策为 `吸收`：`git merge-tree` 预览无冲突即直接合入，处置填「cherry-pick 合入」（非整提交移植时填「手工移植」），并写 dev 侧提交；有冲突则保留「未处理」与 ⬜，记下冲突文件。
   - 领域决策为 `不同步`：处置填「不同步」，说明写明 dev 中的替代实现或不适用的原因，状态置 ✅。
   - 领域决策为 `逐条评估`：保留「未处理」与 ⬜，需要人工判断。
4. 新增领域时先在「领域决策」表登记决策，再落到批次文件的具体行。领域决策变化时，把该领域下仍为 ⬜ 的行批量回填（通常在最新批次文件里）。

人工确认取向后按四层执行，每层完成后跑一次 `cargo check -p oxideterm-gpui-app`：

1. 路径对齐：对「路径策略」中可对齐路径过双 diff 门禁后取 main 终态，一个路径组一个 dev 提交（提交信息注明来源 main 提交）；台账多行共用同一 dev 侧提交哈希。
2. 依赖升级批次：gpui-ce、russh 等升级单独会话全量验证后一次合入，不混入清理批。
3. PR 粒度移植：特性与大修复批每个 PR 一个决策一个提交，分叉文件按 dev 现状落位。
4. UI 修复簇现场查证：在 dev 代码核对缺陷是否存在，存在则小步移植，不存在则不同步。

## 领域决策

合入偏向：dev 面向调试与嵌入式开发人员，不面向网络运维人员。总体保守：能不合入不合入，dev 为主。该偏向是处置的判断依据，不按类别预设结果：底层升级、性能优化与缺陷修复可合入；明确服务调试/嵌入式工作流的提交（含 MCP/agent 工具链、串口与嵌入式传输等方向内功能）按领域决策正常处理；运维向的管理面板与批量运维功能按「不同步」处置并写明理由；契合度拿不准的保留 ⬜ 逐条评估，人工裁决仍拿不准时不合入。合入冲突以 dev 现行为准。新功能不经人工确认不吸收。

dev 自合并基点 `f2593f3bd` 起改动 270 个文件，集中在 `gpui-app`(100)、`i18n`(77)、`alacritty-terminal`(17)、`oxideterm-terminal`(10)、`gpui-ide`(9)、`connections`(9)。`gpui-ce`、`editor-core`、`editor-syntax`、`gpui-editor`、`ide-core`、`ide-fs`、`oxideterm-sftp` 零改动。

| 领域 | 决策 | 依据 |
| --- | --- | --- |
| 应用层 UI | 不同步 | dev 已重构 sidebar、sftp 交互、session manager；`gpui-app` 100 文件自研，main 的功能在此无宿主 |
| 编辑器 / IDE 内核 | 吸收 | dev 仅分叉 `gpui-ide` 9 文件，`editor-core`、`editor-syntax`、`gpui-editor` 零改动 |
| 渲染 / 图形底座 | 吸收 | `gpui-ce` 零改动，性能提交可直接落地 |
| 终端内核 | 吸收 | `oxideterm-terminal` 10 文件，冲突局限在 `search.rs` |
| 终端 UI | 不同步 | 纯视觉口味（滚动条宽度等），dev 自行决定 |
| 存储 / 内存 | 吸收 | 缓存上限与持久化路径，与 dev 改动正交 |
| 云同步 | 逐条评估 | dev 已重构 `gpui-cloud-sync`，需确认冲突是否为真分叉 |
| 协议 / 依赖底层 | 吸收 | `oxideterm-ssh` 1 文件；russh 定制补丁在 0.65 分支保留 |
| 平台集成（BLE） | 不同步 | dev 无 `oxideterm-ble`，属新功能而非能力升级 |
| 文档 | 跟随所属代码领域 | 代码未吸收则文档无落点 |
| 测试 | 跟随所属代码领域 | 同上 |
| CI | 已同步 | — |

## 路径策略

路径策略是合入偏向的执行化：筛选按提交，执行按路径。任何路径对齐前先过双 diff 门禁——`git diff <链条首笔>^ dev -- <路径>` 为空（dev 在改动前与 main 一致），且 `git diff dev <目标提交> -- <路径>` 恰为待吸收改动；目标提交之后若还有同路径改动（如 #64 之于 grid），取链条末笔而非 tip。任一门禁不满足则退回手工移植。

| 路径 | 策略 | 说明 |
| --- | --- | --- |
| `crates/vte/`、`crates/oxideterm-terminal-encoding/`、`crates/oxideterm-modem-transfer/`、`crates/oxideterm-environment/` | 路径对齐 | vendored/底层，已验证零自研 |
| `crates/alacritty-terminal/src/grid/` | 路径对齐 | 已验证零自研；alacritty 其余文件有自研分叉 |
| `crates/oxideterm-terminal/src/session.rs` | 逐条评估 | 有 143 行自研分叉，修复走补丁手工移植 |
| `crates/oxideterm-editor-core/`、`crates/oxideterm-editor-syntax/`、`crates/oxideterm-gpui-editor/` | 路径对齐 | 编辑器内核零自研；gpui-editor 与 gpui-ce 升级联动 |
| `crates/oxideterm-sftp/`、`crates/russh-sftp/`、`crates/oxideterm-ide-fs/`、`crates/oxideterm-preview/`、`crates/oxideterm-tmux/` | 路径对齐 | 协议/存储层零自研 |
| `crates/oxideterm-connection-monitor/` | 路径对齐 | 监控代码面；gpui-app 侧接线除外 |
| `crates/gpui-ce/` | 独立升级批次 | 依赖升级单独会话全量验证，不混入清理批 |
| `crates/oxideterm-ssh/` | 逐条评估 | connection_trace 含 BLE 内容；按文件过门禁后对齐 |
| `crates/oxideterm-terminal/`、`crates/oxideterm-gpui-terminal/` | 逐条评估 | 多处自研分叉与历史冲突点；逐文件过门禁 |
| `crates/oxideterm-gpui-app/` | 永不跟随 | 产品 UI 自研区；bug 修复现场查证后小步移植 |
| `crates/oxideterm-i18n/locales/` | 手工 | 11 语言包逐键合并 |
| `crates/oxideterm-ble/`、`**/ble*` | 永不跟随 | 领域决策 |
| `docs/`、`README*` | 跟随代码领域 | fork 文案自持 |
| `.github/` | 对齐 | CI 维持同步 |
