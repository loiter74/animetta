# mc-mcp

Independent Mineflayer runtime and loopback Streamable HTTP MCP service.

The in-repository service was imported from the former mc-bot baseline commit
`94923f0eaf07bcf456bb277d4a00d97d7956c83c`. This directory is now the canonical
source and does not depend on another checkout.

## 运行方式

`mc-mcp` owns Minecraft server, bot, viewer controller and GameBot v2 runtime
lifecycle. Profiles live in `services/mc-mcp/config/mc-mcp.json`:

- `managed`: starts and probes the repository-owned Compose service, then logs in the
  bot. Shutdown uses the exact persisted ownership identity.
- `external`: probes and connects to an existing server and never stops it.

```bash
npm ci --prefix services/mc-mcp
node services/mc-mcp/src/mcp/cli.js service ensure
node services/mc-mcp/src/mcp/cli.js connect
node services/mc-mcp/src/mcp/cli.js status
node services/mc-mcp/src/mcp/cli.js reattach-viewer
node services/mc-mcp/src/mcp/cli.js disconnect
node services/mc-mcp/src/mcp/cli.js shutdown
node services/mc-mcp/src/mcp/cli.js service stop
```

Run these commands from the repository root. Animetta automatically falls back to this
in-repository CLI entrypoint, so no global installation is required.

The default `connect` target is `external-local`, which reuses the existing server on
`127.0.0.1:25565`. Managed profiles cannot create a Compose project unless the caller
passes `--allow-create`; `prepare` also requires an explicit profile. Creation requires
explicit authorization for either a permanent server or an isolated review world.
Only temporary review worlds must call `shutdown` when the run finishes; a permanent
server remains available for later `external-local` connections.

### 长期本地服务器

`managed-local` 用于首次部署或恢复固定服务器：容器名 `animetta-mc`，Compose
项目 `mc-mcp-managed-local`，世界卷 `animetta-mc-data`，仅监听
`127.0.0.1:25565`。Minecraft Java 版本固定为 `1.21`，采用生存模式。
`restart: unless-stopped` 会在 Docker 引擎恢复后自动启动未被手动停止的容器；
它不负责启动 Docker Desktop。世界数据保存在命名卷中，不能删除该卷来重置服务。

用户明确授权首次部署后，通过现有 mc-mcp 生命周期执行：

```bash
node services/mc-mcp/src/mcp/cli.js prepare managed-local --allow-create
node services/mc-mcp/src/mcp/cli.js disconnect
node services/mc-mcp/src/mcp/cli.js connect external-local
```

`disconnect` 将准备阶段切回可连接状态并保留服务器。日常连接仍使用默认
`external-local`；Anima 通过公开 `mc_connection` 连接，再经 `mc_operate_bot`
执行任务。外部连接的 `shutdown`、普通 `disconnect` 和 service stop 都保留
长期服务器。只有显式选择托管服务器并要求停止时，才使用 managed `shutdown`。
临时评审继续使用独立的 review profile，不复用长期世界进行管理员场景布置。

`disconnect` stops only the bot. `shutdown` additionally stops only managed resources
owned by the current mc-mcp service. The HTTP endpoint defaults to
`http://127.0.0.1:8768/mcp` and requires a locally generated bearer token; CLI output
redacts it except for the machine-readable `service ensure` descriptor consumed by a
local client.

`prepare` is the deployment/bootstrap phase: it downloads and starts the managed server
without logging in the bot. Goal-serving deployments run it before accepting Minecraft
instructions. Connection profiles then enforce a 60-second command-to-`ready` SLO and reserve
45 seconds for server health and 10 seconds for bot login. The managed data volume is
retained across `shutdown`, so the server jar and world are reused instead of downloaded
and generated again. `MC_MCP_REQUEST_TIMEOUT_MS` may be lowered for stricter callers;
raising it does not relax the profile lifecycle deadline.

Use `managed-survival` for autonomous technology progression. It owns an isolated,
persistent default world on port `25567`; peaceful difficulty removes combat starvation
noise while preserving survival mining, crafting, smelting, tool tiers and natural ore
generation. The review profiles remain unchanged.

`mc-mcp service stop` stops the bot and local MCP HTTP service but preserves a managed
server and its ownership record. Use `mc-mcp shutdown` only when the owned server should
also be stopped.

## Viewer policy

Each profile can define `viewer.username`, `viewer.auto_attach` and
`viewer.required`. The Mineflayer viewer controller retries attachment after viewer
join, bot spawn/respawn, dimension changes and periodic checks. Required attachment
failure prevents `ready`; optional failure is reported without blocking the bot.

## Runtime contract

mc-mcp exposes lifecycle tools plus GameBot v2 manifest, observe, execute, inspect,
cancel, health and cursor-based event reads. The internal JSON-line process protocol
between mc-mcp and `src/index.js` is private to this repository. The bot child accepts
only GameBot v2 commands plus the bounded survival-review and viewer lifecycle commands;
the former v1 evaluator, arbitrary-code, Voyager mode and plan protocols are not exposed.

`src/runtime/gamebotV2Adapter.js` owns v2 capability and observation composition,
`src/runtime/processProtocol.js` owns the child-process envelope, and `src/mcp/` owns
profile, managed-server and HTTP MCP lifecycle concerns. The root
`contracts/gamebot/v2/` directory is the only contract source.

## Development

From the repository root:

```bash
npm test --prefix services/mc-mcp
npm run test:contract --prefix services/mc-mcp
npm run check --prefix services/mc-mcp
```
