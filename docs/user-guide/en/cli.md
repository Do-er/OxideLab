# CLI Companion

The `oxidelab` CLI is for headless inspection, automation, CI checks, migration, and recovery. It should not print secret values. Commands that expose credentials should report hints or status only.

## Global Options

```sh
oxidelab --config-dir <path> <command>
oxidelab --profile <name> <command>
OXIDELAB_CONFIG_DIR=<path> oxidelab <command>
```

Use `--json` or `--format json` for scripts. Use `doctor --strict` or command-specific `--strict` flags when warnings should fail CI.

Most write commands share the same safety flags:

- `--dry-run`: show the plan without writing.
- `--yes`: confirm a real write.
- `--json` or `--format json`: produce machine-readable output.

## Diagnostics

```sh
oxidelab paths --json
oxidelab diagnose --json
oxidelab doctor --strict
oxidelab report --json
```

Use `report --bundle <path>` when preparing a support bundle. Review the bundle before sharing it.

## Settings

```sh
oxidelab settings validate --strict
oxidelab settings sections --json
oxidelab settings get ai.providers --json
oxidelab settings set terminal.fontSize 14 --dry-run
oxidelab settings export --section appearance --json
oxidelab settings diff ./settings-snapshot.json --section appearance
```

`set` and `unset` update existing JSON paths only. Use `--yes` to confirm writes.

## Connections

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

`connections open` resolves an exact saved SSH connection name or id, then opens it through the native application's normal saved-connection flow. The GUI remains responsible for loading credentials, proxy settings, and other connection options.

`connections create` and `connections edit` accept `--totp-credential` with an existing credential's name or ID. Names are matched without case sensitivity; use an ID if several credentials share a name. JSON specs use `totpCredential`, including within `proxyChain` entries, or `clearTotpCredential: true` to remove the target connection's binding. Credential seeds stay in protected storage.

For password or passphrase input, prefer `--password-stdin`, `--password-env`, `--passphrase-stdin`, or `--passphrase-env`. Do not pass secret values directly as shell arguments.

## Backups and Restore

```sh
oxidelab backup create --output ./oxideterm-backup.json --json
oxidelab backup inspect ./oxideterm-backup.json --summary
oxidelab backup restore ./oxideterm-backup.json --section settings --dry-run --json
```

Restore commands should be reviewed in dry-run form before `--yes`.

## Cloud Sync

```sh
oxidelab cloud-sync status --json
oxidelab cloud-sync diff --dirty-only --format table
oxidelab cloud-sync backend webdav configure --endpoint https://example.invalid/sync --dry-run
oxidelab cloud-sync sync --dry-run --json
oxidelab cloud-sync sync --yes --json
oxidelab cloud-sync secrets status --json
```

Close the desktop app before running CLI sync, including a dry-run: the command requires exclusive access to the configuration. `sync --dry-run` prepares a plan from the remote backend without applying or publishing it. `preview` and `diff` inspect cached state. Review the plan before using `--yes`.

The current causal sync merges independent changes. The retained `push`, `pull` and `apply --from remote` commands use the same merge coordinator; their names do not select upload-only or download-only behavior. `pull` and `apply` accept only the merge strategy. Choose individual remote conflict candidates in the desktop preview. `resolve --strategy local-wins` selects local candidates for conflicts; inspect its dry-run before applying. Archive-import strategies such as skip, rename and replace belong to `.oxide` imports.

Local application and remote publication have separate outcomes. If publication fails after local changes were applied, retain the configuration and retry sync. See [conflicts and interrupted sync](cloud-sync-and-backups.md#conflicts-and-interrupted-sync) for recovery.

Secret commands must only print hints or status. Use stdin or environment variables for secret writes.

## External MCP stdio bridge

When an external client supports stdio MCP only, first create a client under **Settings → Network & Proxy → External MCP Control** and copy its one-time credential. Configure the client command as:

```sh
OXIDELAB_MCP_TOKEN='<client credential>' oxidelab mcp bridge
```

CC Switch and similar clients that accept one MCP server object can use:

```json
{
  "command": "oxidelab",
  "args": ["mcp", "bridge"],
  "env": {
    "OXIDELAB_MCP_TOKEN": "<client credential>"
  }
}
```

For clients that require a top-level `mcpServers` object, place this object under `mcpServers.oxideterm`.

The bridge discovers the running loopback endpoint from the active configuration directory. Add the same `--profile` or `--config-dir` used by the app when applicable. Set `OXIDELAB_MCP_ENDPOINT` or `--endpoint` only when automatic discovery is unavailable; the override must still be an HTTP `/mcp` URL on `localhost`, `127.0.0.1`, or `::1`. Store the credential in the external client's secret environment settings, never in command arguments, logs, or project files.

## Batch Plans

Batch plans combine several changes into one reviewed operation:

```sh
oxidelab batch apply ./plan.json --dry-run
oxidelab batch apply ./plan.json --yes --json
```

Use batch mode for scripted setup where settings, connection snapshots, and cloud-sync configuration should be reviewed together.

## Completion

```sh
oxidelab completion zsh > ~/.zfunc/_oxidelab
oxidelab completion path zsh
oxidelab completion install zsh
```

Use `--force` with `completion install` only when replacing an existing generated completion file.
