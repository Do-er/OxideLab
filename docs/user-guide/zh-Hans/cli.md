# CLI 伴侣工具

`oxidelab` CLI 用于无界面检查、自动化、CI 校验、迁移和恢复。它不应该打印凭据值；涉及凭据的命令只输出提示或状态。

## 全局选项

```sh
oxidelab --config-dir <path> <command>
oxidelab --profile <name> <command>
OXIDELAB_CONFIG_DIR=<path> oxidelab <command>
```

脚本使用 `--json` 或 `--format json`。CI 中如果警告也应该失败，使用 `doctor --strict` 或命令自己的 `--strict`。

多数写命令共享同一组安全选项：

- `--dry-run`：只显示计划，不写入。
- `--yes`：确认真实写入。
- `--json` 或 `--format json`：输出机器可读结果。

## 诊断

```sh
oxidelab paths --json
oxidelab diagnose --json
oxidelab doctor --strict
oxidelab report --json
```

准备问题报告或支持信息时使用 `report --bundle <path>`。分享前应先检查支持包内容。

## 设置

```sh
oxidelab settings validate --strict
oxidelab settings sections --json
oxidelab settings get ai.providers --json
oxidelab settings set terminal.fontSize 14 --dry-run
oxidelab settings export --section appearance --json
oxidelab settings diff ./settings-snapshot.json --section appearance
```

`set` 和 `unset` 只修改已经存在的 JSON path。真实写入需要显式加 `--yes`。

## 连接

```sh
oxidelab connections list
oxidelab connections search prod --json
oxidelab connections open prod
oxidelab connections create --name prod --host example.internal --user deploy --port 22 --dry-run
oxidelab connections edit prod --totp-credential "Shared MFA" --dry-run
oxidelab connections edit prod --clear-totp-credential --dry-run
oxidelab connections rename prod production --yes
oxidelab connections validate --strict
oxidelab connections export --format raw-safe --json
```

`connections open` 会按完整名称或 ID 查找已保存的 SSH 连接，再通过原生应用既有的保存连接流程打开。凭据、代理设置和其他连接选项仍由 GUI 负责读取。

`connections create` 和 `connections edit` 支持通过 `--totp-credential` 指定已有验证码凭据的名称或 ID。名称匹配不区分大小写；遇到重名时使用 ID。JSON 规格使用 `totpCredential`，`proxyChain` 中的跳板也可指定；使用 `clearTotpCredential: true` 可移除目标连接的关联。验证码密钥仍保存在受保护的存储中。

密码或密钥口令输入优先使用 `--password-stdin`、`--password-env`、`--passphrase-stdin` 或 `--passphrase-env`。不要把凭据值直接写进 shell 参数。

## 备份与恢复

```sh
oxidelab backup create --output ./oxideterm-backup.json --json
oxidelab backup inspect ./oxideterm-backup.json --summary
oxidelab backup restore ./oxideterm-backup.json --section settings --dry-run --json
```

恢复命令应先用 `--dry-run` 检查计划，再用 `--yes` 确认真执行。

## 云同步

```sh
oxidelab cloud-sync status --json
oxidelab cloud-sync diff --dirty-only --format table
oxidelab cloud-sync backend webdav configure --endpoint https://example.invalid/sync --dry-run
oxidelab cloud-sync sync --dry-run --json
oxidelab cloud-sync sync --yes --json
oxidelab cloud-sync secrets status --json
```

运行 CLI 同步前先关闭桌面应用，包括试运行：命令需要独占配置。`sync --dry-run` 从远端后端准备计划，不应用也不发布；`preview` 和 `diff` 查看缓存状态。检查计划后再使用 `--yes`。

当前因果同步会合并独立变更。保留的 `push`、`pull` 和 `apply --from remote` 命令使用同一合并协调器，名称不表示仅上传或仅下载。`pull` 和 `apply` 只接受 merge 策略。逐项选择远端冲突候选应使用桌面预览；`resolve --strategy local-wins` 为冲突选择本地候选，应用前先检查试运行结果。skip、rename、replace 等归档导入策略用于 `.oxide` 导入。

本地应用与远端发布具有独立结果。本地变更应用后若发布失败，应保留配置并重试同步。恢复步骤参见[冲突与中断恢复](cloud-sync-and-backups.md#冲突与中断恢复)。

凭据命令只能输出提示或状态。写入凭据时使用标准输入或环境变量。

## 外部 MCP stdio bridge

外部客户端只支持 stdio MCP 时，先在 OxideLab 的“设置 → 网络与代理 → 外部 MCP 控制”创建客户端并复制只显示一次的凭据，再把客户端命令配置为：

```sh
OXIDELAB_MCP_TOKEN='<客户端凭据>' oxidelab mcp bridge
```

CC Switch 等接受单个 MCP 服务对象的客户端可以使用：

```json
{
  "command": "oxidelab",
  "args": ["mcp", "bridge"],
  "env": {
    "OXIDELAB_MCP_TOKEN": "<客户端凭据>"
  }
}
```

需要顶层 `mcpServers` 的客户端则把该对象放到 `mcpServers.oxidelab` 下。

bridge 会从当前配置目录发现正在运行的回环端点。使用命名 profile 时，客户端命令也要带相同的 `--profile`；自定义配置目录则带 `--config-dir`。只有自动发现不可用时才设置 `OXIDELAB_MCP_ENDPOINT` 或 `--endpoint`，且它必须是 `http://localhost.../mcp`、`127.0.0.1` 或 `::1`。凭据只能放在外部客户端的秘密环境设置中，不要放进命令参数、日志或项目文件。

## Batch Plans

batch plan 可以把多个变更合并成一次可审查操作：

```sh
oxidelab batch apply ./plan.json --dry-run
oxidelab batch apply ./plan.json --yes --json
```

当设置、连接快照和云同步配置需要一起审查时，使用批处理模式。

## Shell Completion

```sh
oxidelab completion zsh > ~/.zfunc/_oxidelab
oxidelab completion path zsh
oxidelab completion install zsh
```

只有在确定要覆盖已有 completion 文件时才给 `completion install` 加 `--force`。
