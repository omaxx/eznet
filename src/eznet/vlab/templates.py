"""Device definitions for virtual lab deployment."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from eznet.qemu.vm import VM, Disk, Interface
from eznet.host.config import UserData, NetworkConfig


# ---------------------------------------------------------------------------
# Interface factory functions
# ---------------------------------------------------------------------------

def bridge(name: str, *, mac: str | None = None) -> Interface:
    """Creates a bridge interface.

    Args:
        name: Host bridge name (e.g. 'br0', 'mgmt').
        mac: Optional MAC address.

    Returns:
        An ``Interface`` configured for bridge mode.
    """
    return Interface(type="bridge", source=name, target=name, mac=mac)


def network(name: str, *, mac: str | None = None) -> Interface:
    """Creates a libvirt network interface.

    Args:
        name: Libvirt network name (e.g. 'default', 'p2p-1').
        mac: Optional MAC address.

    Returns:
        An ``Interface`` configured for network mode.
    """
    return Interface(type="network", source=name, target=name, mac=mac)


def peer(
    *,
    local_address: str,
    local_port: int,
    remote_address: str,
    remote_port: int,
    mac: str | None = None,
) -> Interface:
    """Creates a UDP tunnel (peer-to-peer) interface.

    Args:
        local_address: Local bind address.
        local_port: Local bind port.
        remote_address: Remote peer address.
        remote_port: Remote peer port.
        mac: Optional MAC address.

    Returns:
        An ``Interface`` configured for UDP tunnel mode.
    """
    return Interface(
        type="udp",
        source=f"{remote_address}:{remote_port}",
        target=f"{local_address}:{local_port}",
        mac=mac,
    )


# ---------------------------------------------------------------------------
# Template data structures
# ---------------------------------------------------------------------------

@dataclass
class ImageTask:
    """Describes an image to provision for a VM.

    Attributes:
        source: Path to the base image, relative to the images directory.
        filename: Destination filename inside the VM directory.
        mode: Provisioning method.
    """

    source: str
    filename: str
    mode: Literal["copy", "snapshot"] = "snapshot"


@dataclass
class InitConfig:
    """Initial configuration to apply inside a VM directory.

    Attributes:
        files: Mapping of ``{filename: content}`` to write.
        commands: Shell commands to execute on the host (in order).
    """

    files: dict[str, str] = field(default_factory=dict)
    commands: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Abstract template
# ---------------------------------------------------------------------------

class Template(ABC):
    """Abstract base for device templates.

    A template describes one or more VMs that make up a device. It
    provides all the information VLab needs to deploy them without
    executing any host commands itself.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Device name (used as the top-level directory)."""

    @abstractmethod
    def vm_names(self) -> list[str]:
        """Returns the names of all VMs in this device."""

    @abstractmethod
    def images(self, vm_name: str) -> list[ImageTask]:
        """Returns images to provision for a given VM.

        Args:
            vm_name: Name of the VM.

        Returns:
            A list of ``ImageTask`` describing images to copy or snapshot.
        """

    @abstractmethod
    def init(self, vm_name: str, vm_path: str) -> InitConfig:
        """Returns the initial configuration for a given VM.

        Args:
            vm_name: Name of the VM.
            vm_path: Absolute path to the VM directory on the host.

        Returns:
            An ``InitConfig`` with files to write and commands to run.
        """

    @abstractmethod
    def domain(self, vm_name: str, vm_path: str) -> VM:
        """Returns the libvirt domain definition for a given VM.

        Args:
            vm_name: Name of the VM.
            vm_path: Absolute path to the VM directory on the host.

        Returns:
            A ``VM`` dataclass ready for XML generation.
        """


# ---------------------------------------------------------------------------
# Linux device (single VM)
# ---------------------------------------------------------------------------

@dataclass
class Linux(Template):
    """Single Linux VM device.

    Attributes:
        name: VM name (must be unique per host).
        image: Path to the base image relative to the images directory.
        image_mode: Provisioning method for the disk image.
        vcpus: Number of virtual CPUs.
        memory_mb: Memory in megabytes.
        interfaces: Network interfaces. Use ``bridge()``, ``network()``,
            and ``peer()`` helpers to create them.
        user_data: Cloud-init user-data configuration. Optional.
        network_config: Cloud-init network configuration. Optional.
    """

    name: str = ""
    image: str = ""
    image_mode: Literal["copy", "snapshot"] = "snapshot"
    vcpus: int = 1
    memory_mb: int = 1024
    interfaces: list[Interface] = field(default_factory=list)
    user_data: UserData | None = None
    network_config: NetworkConfig | None = None

    def vm_names(self) -> list[str]:
        return [self.name]

    def images(self, vm_name: str) -> list[ImageTask]:
        return [
            ImageTask(
                source=self.image,
                filename=Path(self.image).name,
                mode=self.image_mode,
            ),
        ]

    def init(self, vm_name: str, vm_path: str) -> InitConfig:
        files: dict[str, str] = {
            "meta-data": (
                f"instance-id: {self.name}\n"
                f"local-hostname: {self.name}\n"
            ),
        }
        if self.user_data is not None:
            files["user-data"] = str(self.user_data)
        if self.network_config is not None:
            files["network-config"] = str(self.network_config)

        seed_path = f"{vm_path}/seed.img"
        cmd = f"cloud-localds {seed_path}"
        if self.network_config is not None:
            cmd += f" --network-config {vm_path}/network-config"
        cmd += f" {vm_path}/user-data {vm_path}/meta-data"

        return InitConfig(files=files, commands=[cmd])

    def domain(self, vm_name: str, vm_path: str) -> VM:
        image_path = f"{vm_path}/{Path(self.image).name}"
        seed_path = f"{vm_path}/seed.img"
        return VM(
            name=self.name,
            vcpus=self.vcpus,
            memory_mb=self.memory_mb,
            disks=[
                Disk(source=image_path, target="vda", format="qcow2"),
                Disk(source=seed_path, target="vdb", format="raw"),
            ],
            interfaces=self.interfaces,
        )