"""Channel abstractions for fault injector and load simulator."""

from .base import BaseChannel, ChannelResult, JsonlWalHook, LocalShellChannel
from .cube_studio import CubeStudioChannel
from .kubernetes import KubernetesChannel
from .prometheus import PrometheusChannel
from .redfish import RedfishChannel
from .ssh import HostSpec, SSHChannel
from .switch import SwitchChannel

__all__ = [
    "BaseChannel",
    "ChannelResult",
    "CubeStudioChannel",
    "HostSpec",
    "JsonlWalHook",
    "KubernetesChannel",
    "LocalShellChannel",
    "PrometheusChannel",
    "RedfishChannel",
    "SSHChannel",
    "SwitchChannel",
]
