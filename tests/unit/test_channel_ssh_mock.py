from __future__ import annotations

from channel.ssh import HostSpec, SSHChannel


def test_ssh_channel_simulate_updates_mtu_state() -> None:
    channel = SSHChannel(mode="simulate")
    host = HostSpec(name="node-a", host="127.0.0.1", user="root")

    channel.seed_simulated_mtu("node-a", "eth0", 4200)
    result = channel.execute(host, "sudo ip link set dev eth0 mtu 1500")

    assert result.success is True
    assert result.simulated is True
    assert channel.get_simulated_mtu("node-a", "eth0") == 1500
