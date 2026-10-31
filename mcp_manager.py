"""Runtime connections to configured MCP servers."""

import asyncio
import ipaddress
import json
import os
import re
import shutil
import socket
from contextlib import AsyncExitStack
from pathlib import Path
from urllib.parse import urlsplit


_ALIAS_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,31}$")
_PACKAGE_RE = re.compile(r"^@?[a-zA-Z0-9][a-zA-Z0-9._/-]{0,127}$")
_ENV_RE = re.compile(r"^[A-Za-z_]\w*$", re.ASCII)
_MAX_ARGUMENT_BYTES = 65536
_MAX_OUTPUT_CHARS = 4000


class MCPConfigError(ValueError):
    """Raised when an MCP server definition is invalid."""


def is_admin_chat_id(chat_id, telegram_admin_id, discord_admin_id):
    chat_id = str(chat_id)
    if chat_id.startswith("dc:"):
        configured_id = discord_admin_id
        chat_id = chat_id[3:]
        if configured_id is not None:
            configured_id = str(configured_id).removeprefix("dc:")
    else:
        configured_id = telegram_admin_id
    return configured_id is not None and chat_id == str(configured_id)


def _resolve_addresses(hostname):
    return {
        info[4][0]
        for info in socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    }


def validate_public_url(url, resolver=_resolve_addresses):
    """Require an HTTPS MCP endpoint whose resolved addresses are public."""
    if not isinstance(url, str) or len(url) > 2048:
        raise MCPConfigError("The MCP URL is invalid or too long.")

    parsed = urlsplit(url)
    if (
        parsed.scheme.lower() != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise MCPConfigError(
            "MCP HTTP endpoints must be HTTPS URLs without credentials, query strings, or fragments."
        )

    try:
        parsed.port
    except ValueError as error:
        raise MCPConfigError("The MCP URL has an invalid port.") from error

    try:
        addresses = resolver(parsed.hostname)
    except (OSError, ValueError) as error:
        raise MCPConfigError("The MCP host could not be resolved.") from error

    if not addresses:
        raise MCPConfigError("The MCP host did not resolve to an address.")
    for address in addresses:
        try:
            if not ipaddress.ip_address(address).is_global:
                raise MCPConfigError("MCP HTTP endpoints must resolve only to public IP addresses.")
        except ValueError as error:
            raise MCPConfigError("The MCP host resolved to an invalid IP address.") from error
    return url


def _validate_alias(alias):
    if not isinstance(alias, str) or not _ALIAS_RE.fullmatch(alias):
        raise MCPConfigError("Aliases must be 1-32 letters, digits, underscores, or hyphens.")
    return alias


def _normalize_http_config(config, alias, resolver):
    token_env = config.get("token_env")
    if token_env is not None and (
        not isinstance(token_env, str) or not _ENV_RE.fullmatch(token_env)
    ):
        raise MCPConfigError("token_env must be a valid environment variable name.")
    return {
        "alias": alias,
        "transport": "http",
        "url": validate_public_url(config.get("url"), resolver),
        "token_env": token_env,
    }


def _valid_package_identifier(value):
    return (
        isinstance(value, str)
        and _PACKAGE_RE.fullmatch(value) is not None
        and ".." not in value
    )


def _normalize_stdio_args(config):
    args = config.get("args", [])
    if not isinstance(args, list) or len(args) > 64:
        raise MCPConfigError("stdio args must be a list of at most 64 short strings.")
    if any(not isinstance(arg, str) or "\x00" in arg or len(arg) > 2048 for arg in args):
        raise MCPConfigError("stdio args must be a list of at most 64 short strings.")
    return args


def _normalize_stdio_env(config):
    env = config.get("env", {})
    if not isinstance(env, dict) or len(env) > 32:
        raise MCPConfigError("stdio env must map environment names to variable references.")
    resolved_env = {}
    for name, variable in env.items():
        if (
            not isinstance(name, str)
            or not _ENV_RE.fullmatch(name)
            or not isinstance(variable, str)
            or not _ENV_RE.fullmatch(variable)
        ):
            raise MCPConfigError("stdio env values must be environment variable names.")
        resolved_env[name] = variable
    return resolved_env


def _normalize_stdio_config(config, alias):
    package_manager = config.get("package_manager")
    package = config.get("package")
    if package_manager not in {"npx", "uvx"}:
        raise MCPConfigError("stdio package_manager must be 'npx' or 'uvx'.")
    if not _valid_package_identifier(package):
        raise MCPConfigError("The stdio package identifier is invalid.")

    args = _normalize_stdio_args(config)
    resolved_env = _normalize_stdio_env(config)

    entrypoint = config.get("entrypoint")
    if package_manager == "uvx" and not _valid_package_identifier(entrypoint):
        raise MCPConfigError("uvx servers must specify a valid package entrypoint.")

    normalized = {
        "alias": alias,
        "transport": "stdio",
        "package_manager": package_manager,
        "package": package,
        "args": args,
        "env": resolved_env,
    }
    if package_manager == "uvx":
        normalized["entrypoint"] = entrypoint
    return normalized


def normalize_server_config(config, resolver=_resolve_addresses):
    """Validate and normalize a persisted or newly submitted server definition."""
    if not isinstance(config, dict):
        raise MCPConfigError("An MCP server definition must be an object.")

    alias = _validate_alias(config.get("alias"))
    transport = config.get("transport")
    if transport == "http":
        return _normalize_http_config(config, alias, resolver)
    if transport != "stdio":
        raise MCPConfigError("Transport must be 'stdio' or 'http'.")
    return _normalize_stdio_config(config, alias)


def build_stdio_command(config, windows=None, executable_lookup=shutil.which):
    """Build an argv vector without invoking a shell."""
    config = normalize_server_config(config)
    if config["transport"] != "stdio":
        raise MCPConfigError("Only stdio definitions have a package command.")
    if config["package_manager"] == "npx":
        if windows is None:
            windows = os.name == "nt"
        if windows:
            node = executable_lookup("node")
            if not node:
                raise MCPConfigError("Node.js is required to run npx MCP servers.")
            node_directory = Path(node).parent
            candidates = [
                node_directory / "node_modules" / "npm" / "bin" / "npx-cli.js"
            ]
            app_data = os.environ.get("APPDATA")
            if app_data:
                candidates.append(
                    Path(app_data)
                    / "npm"
                    / "node_modules"
                    / "npm"
                    / "bin"
                    / "npx-cli.js"
                )
            npx_cli = next((path for path in candidates if path.is_file()), None)
            if npx_cli is None:
                raise MCPConfigError("Could not locate npm's npx-cli.js entrypoint.")
            return node, [str(npx_cli), "--yes", config["package"], *config["args"]]
        return "npx", ["--yes", config["package"], *config["args"]]
    return "uvx", [
        "--from",
        config["package"],
        config["entrypoint"],
        *config["args"],
    ]


class MCPManager:
    """Persist server definitions and maintain connected MCP clients."""

    def __init__(
        self, registry_path="mcp_servers.json", resolver=_resolve_addresses, client_factory=None
    ):
        self.registry_path = Path(registry_path)
        self.resolver = resolver
        self.client_factory = client_factory
        self.servers = {}
        self.connections = {}
        self._lock = asyncio.Lock()
        self._pending_aliases = set()
        self._reconnecting = set()
        self._loaded = False

    async def load(self):
        """Load saved definitions and attempt each connection independently."""
        if self._loaded:
            return
        self._loaded = True
        if not self.registry_path.exists():
            return

        try:
            data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise MCPConfigError("The MCP registry could not be read.") from error
        if not isinstance(data, list):
            raise MCPConfigError("The MCP registry must contain a list.")

        for entry in data:
            normalized = await asyncio.to_thread(
                normalize_server_config, entry, self.resolver
            )
            if normalized["alias"] in self.servers:
                raise MCPConfigError("The MCP registry contains a duplicate alias.")
            self.servers[normalized["alias"]] = normalized

        for alias in tuple(self.servers):
            try:
                await self._connect(alias)
            except Exception as error:
                print(f"[MCP] Could not reconnect '{alias}': {error}")

    async def add(self, config):
        """Connect a server, then persist it only after tools are available."""
        normalized = await asyncio.to_thread(
            normalize_server_config, config, self.resolver
        )
        alias = normalized["alias"]
        async with self._lock:
            if alias in self.servers or alias in self._pending_aliases:
                raise MCPConfigError(f"MCP alias '{alias}' is already registered.")
            self._pending_aliases.add(alias)
        try:
            await self._connect_config(normalized)
            async with self._lock:
                self.servers[alias] = normalized
                try:
                    self._save()
                except Exception:
                    self.servers.pop(alias, None)
                    connection = self.connections.pop(alias, None)
                    if connection:
                        await connection["stack"].aclose()
                    raise
        finally:
            async with self._lock:
                self._pending_aliases.discard(alias)

    async def remove(self, alias):
        async with self._lock:
            if alias not in self.servers:
                raise MCPConfigError(f"MCP server '{alias}' is not registered.")
            if alias in self._reconnecting:
                raise MCPConfigError(f"MCP server '{alias}' is reconnecting.")
            connection = self.connections.get(alias)
            updated_servers = dict(self.servers)
            del updated_servers[alias]
            self._save(updated_servers)
            self.servers = updated_servers
            self.connections.pop(alias, None)
        if connection:
            async with connection["lock"]:
                await connection["stack"].aclose()

    async def reconnect(self, alias):
        async with self._lock:
            if alias not in self.servers:
                raise MCPConfigError(f"MCP server '{alias}' is not registered.")
            if alias in self._reconnecting:
                raise MCPConfigError(f"MCP server '{alias}' is already reconnecting.")
            self._reconnecting.add(alias)
            config = self.servers[alias]
            connection = self.connections.pop(alias, None)
        try:
            if connection:
                async with connection["lock"]:
                    await connection["stack"].aclose()
            await self._connect_config(config)
        finally:
            async with self._lock:
                self._reconnecting.discard(alias)

    def list_servers(self):
        return [
            {
                "alias": alias,
                "transport": config["transport"],
                "connected": alias in self.connections,
                "tools": [tool.name for tool in self.connections.get(alias, {}).get("tools", [])],
            }
            for alias, config in self.servers.items()
        ]

    def connected_tools(self):
        return [
            (alias, tool)
            for alias, connection in self.connections.items()
            for tool in connection["tools"]
        ]

    async def list_tools(self, alias):
        async with self._lock:
            connection = self.connections.get(alias)
        if not connection:
            raise MCPConfigError(f"MCP server '{alias}' is not connected.")
        return connection["tools"]

    async def call_tool(self, alias, name, arguments):
        async with self._lock:
            connection = self.connections.get(alias)
            if not connection:
                raise MCPConfigError(f"MCP server '{alias}' is not connected.")
            await connection["lock"].acquire()
        try:
            if not isinstance(arguments, dict):
                raise MCPConfigError("Tool arguments must be a JSON object.")
            if len(json.dumps(arguments, ensure_ascii=True).encode("utf-8")) > _MAX_ARGUMENT_BYTES:
                raise MCPConfigError("Tool arguments exceed the 64 KiB limit.")

            tool = next((item for item in connection["tools"] if item.name == name), None)
            if tool is None:
                raise MCPConfigError(f"Tool '{name}' is not offered by server '{alias}'.")
            try:
                from jsonschema import ValidationError, validate

                validate(instance=arguments, schema=tool.input_schema)
            except ImportError as error:
                raise MCPConfigError("Install jsonschema to validate MCP tool arguments.") from error
            except ValidationError as error:
                raise MCPConfigError(f"Tool arguments are invalid: {error.message}") from error

            result = await connection["client"].call_tool(name, arguments)
            content = getattr(result, "structured_content", None)
            if content is None:
                content = [
                    block.text if hasattr(block, "text") else str(block)
                    for block in getattr(result, "content", [])
                ]
            output = json.dumps(content, ensure_ascii=False, default=str)
            if len(output) > _MAX_OUTPUT_CHARS:
                output = output[:_MAX_OUTPUT_CHARS] + "... (truncated)"
            if getattr(result, "is_error", False):
                raise MCPConfigError(output)
            return output
        finally:
            connection["lock"].release()

    async def close(self):
        async with self._lock:
            connections, self.connections = self.connections, {}
        for connection in connections.values():
            async with connection["lock"]:
                await connection["stack"].aclose()

    async def _connect(self, alias):
        await self._connect_config(self.servers[alias])

    async def _connect_config(self, config):
        stack = AsyncExitStack()
        try:
            client = await self._create_client(config, stack)
            await stack.enter_async_context(client)
            tools = await self._list_all_tools(client)
            self.connections[config["alias"]] = {
                "client": client,
                "stack": stack,
                "tools": tools,
                "lock": asyncio.Lock(),
            }
        except Exception:
            await stack.aclose()
            raise

    async def _create_client(self, config, stack):
        if self.client_factory:
            return self.client_factory(config)
        from mcp import Client

        if config["transport"] == "stdio":
            source = self._create_stdio_parameters(config)
        else:
            source = await self._create_http_transport(config, stack)
        return Client(source)

    @staticmethod
    def _create_stdio_parameters(config):
        from mcp import StdioServerParameters

        command, args = build_stdio_command(config)
        env = {}
        for name, variable in config["env"].items():
            value = os.environ.get(variable)
            if value is None:
                raise MCPConfigError(
                    f"Required environment variable '{variable}' is not set."
                )
            env[name] = value
        return StdioServerParameters(command=command, args=args, env=env or None)

    async def _create_http_transport(self, config, stack):
        from mcp.client.streamable_http import streamable_http_client
        import httpx2

        await asyncio.to_thread(validate_public_url, config["url"], self.resolver)
        headers = {}
        token_env = config.get("token_env")
        if token_env:
            token = os.environ.get(token_env)
            if not token:
                raise MCPConfigError(
                    f"Required bearer token variable '{token_env}' is not set."
                )
            headers["Authorization"] = f"Bearer {token}"
        http_client = httpx2.AsyncClient(
            headers=headers,
            timeout=httpx2.Timeout(30.0, read=300.0),
        )
        await stack.enter_async_context(http_client)
        return streamable_http_client(config["url"], http_client=http_client)

    @staticmethod
    async def _list_all_tools(client):
        tools = []
        cursor = None
        while True:
            page = await client.list_tools(cursor=cursor)
            tools.extend(page.tools)
            cursor = page.next_cursor
            if cursor is None:
                return tools

    def _save(self, servers=None):
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.registry_path.with_suffix(self.registry_path.suffix + ".tmp")
        temporary_path.write_text(
            json.dumps(
                list((servers if servers is not None else self.servers).values()),
                indent=2,
            ),
            encoding="utf-8",
        )
        temporary_path.replace(self.registry_path)