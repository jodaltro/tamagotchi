"""
Minimal MCP client stub for the organic virtual pet.

This module provides a lightweight stand‑in for a real Model Context Protocol
client, inspired by the AskIt library. It loads an `mcp_config.json` file
located alongside the code and dispatches method calls to the appropriate
local components (e.g. `PetState` or `MemoryStore`) based on the server
configuration. In a production environment you would replace this stub
with a full MCP client that communicates with remote servers over HTTP or
other transports.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional, Callable

from .pet_state import PetState


class MCPClient:
    """A minimal MCP client that dispatches calls to local pet methods.

    The client reads `mcp_config.json` from the package directory to
    determine which servers are available and their transport type. Only
    servers with `transport` set to ``"local"`` are supported in this stub.
    Each call is forwarded to a method on the provided pet instance.

    Args:
        pet: An instance of :class:`VirtualPet` whose state will be
            manipulated by MCP calls. The client does not persist any state
            itself.
    """

    def __init__(self, pet: "VirtualPet") -> None:
        self.pet = pet
        # Load the MCP configuration file relative to this module
        config_path = os.path.join(os.path.dirname(__file__), "mcp_config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                try:
                    self.config: Dict[str, Any] = json.load(f)
                except Exception:
                    self.config = {}
        else:
            self.config = {}

    async def call(self, server: str, method: str, *args: Any, **kwargs: Any) -> Any:
        """Call a method on a local server.

        This method looks up the requested server in the MCP configuration. If
        the server is configured with a local transport, the call is routed
        to the corresponding object on the pet instance. Otherwise a
        :class:`NotImplementedError` is raised.

        For example, a call to ``("memory_server", "add_episode", text, salience)``
        will be forwarded to ``pet.state.memory.add_episode(text, salience)``.

        Args:
            server: The server name as defined in ``mcp_config.json``.
            method: The method name to invoke on the server.
            *args: Positional arguments passed to the method.
            **kwargs: Keyword arguments passed to the method.

        Returns:
            The return value of the invoked method.

        Raises:
            NotImplementedError: If the server or method is not supported.
        """
        servers = self.config.get("mcpServers", {})
        if server not in servers:
            raise NotImplementedError(f"Unknown MCP server: {server}")
        transport = servers[server].get("transport", "local")
        disabled = servers[server].get("disabled", False)
        if disabled:
            raise NotImplementedError(f"MCP server {server} is disabled")
        if transport != "local":
            raise NotImplementedError(
                f"MCP server {server} uses unsupported transport '{transport}'"
            )
        # Dispatch to local object
        target = self._get_local_target(server)
        if target is None:
            raise NotImplementedError(f"No local target for MCP server {server}")
        if not hasattr(target, method):
            raise NotImplementedError(
                f"MCP method {method} not found on target for server {server}"
            )
        func: Callable[..., Any] = getattr(target, method)
        return func(*args, **kwargs)

    def _get_local_target(self, server: str) -> Optional[Any]:
        """Return the local object corresponding to a server name.

        Currently supports ``memory_server`` and ``pet_state_server``. Other
        server names will result in ``None``.
        """
        if server == "memory_server":
            return self.pet.state.memory
        if server == "pet_state_server":
            return self.pet.state
        return None