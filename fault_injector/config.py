"""Legacy compatibility shim for `fault_injector.config` imports.

The source of truth now lives in the `fault_injector/config/` package.
"""

from fault_injector.config import InjectorConfig, ServerConfig, load_config

__all__ = ["InjectorConfig", "ServerConfig", "load_config"]
