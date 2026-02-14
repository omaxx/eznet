"""Libvirt domain XML builder for KVM virtual machines."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Literal
from xml.etree.ElementTree import Element, SubElement, tostring, indent


@dataclass
class Disk:
    """Single disk attached to a VM.

    Attributes:
        source: Absolute path to the disk image on the host.
        target: Device name inside the guest (e.g. 'vda', 'sdb').
        format: Disk image format.
        bus: Disk bus type.
        device: Disk device type.
    """

    source: str
    target: str
    format: Literal["qcow2", "raw"] = "qcow2"
    bus: Literal["virtio", "scsi", "sata", "ide"] = "virtio"
    device: Literal["disk", "cdrom"] = "disk"

    def xml(self) -> Element:
        """Builds the <disk> element.

        Returns:
            An ``Element`` representing this disk.
        """
        elem = Element("disk", type="file", device=self.device)
        SubElement(elem, "driver", name="qemu", type=self.format)
        SubElement(elem, "source", file=self.source)
        SubElement(elem, "target", dev=self.target, bus=self.bus)
        return elem


@dataclass
class Interface:
    """Single network interface attached to a VM.

    The meaning of ``source`` and ``target`` depends on the interface type:

    - **network**: ``source`` is the libvirt network name, ``target`` is the
      tap device name on the host (e.g. 'vnet0').
    - **bridge**: ``source`` is the host bridge name (e.g. 'br0'), ``target``
      is the tap device name on the host.
    - **udp**: ``source`` is the remote ``address:port``, ``target`` is the
      local ``address:port``.

    Attributes:
        type: Interface connection type.
        source: Source endpoint.
        target: Target endpoint.
        mac: MAC address. Optional.
        model: NIC model type.
    """

    type: Literal["network", "bridge", "udp"]
    source: str
    target: str
    mac: str | None = None
    model: Literal["virtio", "e1000", "rtl8139"] = "virtio"

    def xml(self) -> Element:
        """Builds the <interface> element.

        XML output per type:

        network::

            <interface type='network'>
              <source network='mgmt'/>
              <target dev='vnet0'/>
              <model type='virtio'/>
            </interface>

        bridge::

            <interface type='bridge'>
              <source bridge='br0'/>
              <target dev='vnet0'/>
              <model type='virtio'/>
            </interface>

        udp::

            <interface type='udp'>
              <source address='REMOTE_IP' port='REMOTE_PORT'>
                <local address='LOCAL_IP' port='LOCAL_PORT'/>
              </source>
              <model type='virtio'/>
            </interface>

        Returns:
            An ``Element`` representing this interface.
        """
        elem = Element("interface", type=self.type)

        if self.mac is not None:
            SubElement(elem, "mac", address=self.mac)

        if self.type == "network":
            SubElement(elem, "source", network=self.source)
            SubElement(elem, "target", dev=self.target)

        elif self.type == "bridge":
            SubElement(elem, "source", bridge=self.source)
            SubElement(elem, "target", dev=self.target)

        elif self.type == "udp":
            remote_addr, remote_port = self.source.rsplit(":", 1)
            local_addr, local_port = self.target.rsplit(":", 1)
            source_elem = SubElement(
                elem, "source",
                address=remote_addr, port=remote_port,
            )
            SubElement(
                source_elem, "local",
                address=local_addr, port=local_port,
            )

        SubElement(elem, "model", type=self.model)
        return elem


@dataclass
class Graphics:
    """Graphics device configuration.

    Attributes:
        type: Graphics protocol.
        port: Port number. -1 for autoport.
        listen: Listen address.
    """

    type: Literal["vnc", "spice"] = "vnc"
    port: int = -1
    listen: str = "0.0.0.0"

    def xml(self) -> Element:
        """Builds the <graphics> element.

        Returns:
            An ``Element`` representing this graphics device.
        """
        attrs = {"type": self.type, "listen": self.listen}
        if self.port == -1:
            attrs["autoport"] = "yes"
        else:
            attrs["port"] = str(self.port)
            attrs["autoport"] = "no"

        elem = Element("graphics", **attrs)
        SubElement(elem, "listen", type="address", address=self.listen)
        return elem


@dataclass
class VM:
    """KVM virtual machine definition.

    Produces libvirt-compatible domain XML via the ``xml()`` method.
    Controllers, serial console, input devices, and other boilerplate
    are generated automatically.

    Attributes:
        name: VM name (must be unique per host).
        vcpus: Number of virtual CPUs.
        memory_mb: Memory in megabytes.
        disks: Attached disk images.
        interfaces: Network interfaces.
        graphics: Graphics device configuration.
        arch: CPU architecture.
        machine: QEMU machine type.
        cpu_mode: CPU emulation mode.
        emulator: Path to the QEMU emulator binary.
        uuid: Domain UUID. Auto-generated if not provided.
    """

    name: str
    vcpus: int = 1
    memory_mb: int = 1024
    disks: list[Disk] = field(default_factory=list)
    interfaces: list[Interface] = field(default_factory=list)
    graphics: Graphics = field(default_factory=Graphics)
    arch: Literal["x86_64", "aarch64"] = "x86_64"
    machine: str = "pc-q35-10.0"
    cpu_mode: Literal[
        "host-passthrough", "host-model", "custom"
    ] = "host-passthrough"
    emulator: str = "/usr/bin/qemu-system-x86_64"
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))

    def xml(self) -> str:
        """Builds and returns the libvirt domain XML string.

        Returns:
            A formatted XML string ready for ``virConnect.defineXML()``.
        """
        root = self._build_domain()
        indent(root, space="  ")
        return tostring(root, encoding="unicode", xml_declaration=False)

    def _build_domain(self) -> Element:
        """Constructs the full <domain> element tree."""
        domain = Element("domain", type="kvm")

        SubElement(domain, "name").text = self.name
        SubElement(domain, "uuid").text = self.uuid

        memory_kib = self.memory_mb * 1024
        SubElement(domain, "memory", unit="KiB").text = str(memory_kib)
        SubElement(domain, "currentMemory", unit="KiB").text = str(memory_kib)
        SubElement(domain, "vcpu", placement="static").text = str(self.vcpus)

        self._build_os(domain)
        self._build_features(domain)
        self._build_cpu(domain)
        self._build_clock(domain)
        self._build_power(domain)
        self._build_devices(domain)

        return domain

    def _build_os(self, parent: Element) -> None:
        """Adds <os> section."""
        os_elem = SubElement(parent, "os")
        os_type = SubElement(os_elem, "type", arch=self.arch, machine=self.machine)
        os_type.text = "hvm"
        SubElement(os_elem, "boot", dev="hd")

    def _build_features(self, parent: Element) -> None:
        """Adds <features> section (acpi + apic)."""
        features = SubElement(parent, "features")
        SubElement(features, "acpi")
        SubElement(features, "apic")

    def _build_cpu(self, parent: Element) -> None:
        """Adds <cpu> section."""
        SubElement(
            parent, "cpu",
            mode=self.cpu_mode, check="none", migratable="on",
        )

    def _build_clock(self, parent: Element) -> None:
        """Adds <clock> section with standard timers."""
        clock = SubElement(parent, "clock", offset="utc")
        SubElement(clock, "timer", name="rtc", tickpolicy="catchup")
        SubElement(clock, "timer", name="pit", tickpolicy="delay")
        SubElement(clock, "timer", name="hpet", present="no")

    def _build_power(self, parent: Element) -> None:
        """Adds power management and lifecycle elements."""
        SubElement(parent, "on_poweroff").text = "destroy"
        SubElement(parent, "on_reboot").text = "restart"
        SubElement(parent, "on_crash").text = "destroy"

        pm = SubElement(parent, "pm")
        SubElement(pm, "suspend-to-mem", enabled="no")
        SubElement(pm, "suspend-to-disk", enabled="no")

    def _build_devices(self, parent: Element) -> None:
        """Adds the <devices> section with all hardware."""
        devices = SubElement(parent, "devices")

        SubElement(devices, "emulator").text = self.emulator

        # Disks.
        for disk in self.disks:
            devices.append(disk.xml())

        # Network interfaces.
        for iface in self.interfaces:
            devices.append(iface.xml())

        # Serial console.
        serial = SubElement(devices, "serial", type="pty")
        target = SubElement(serial, "target", type="isa-serial", port="0")
        SubElement(target, "model", name="isa-serial")

        console = SubElement(devices, "console", type="pty")
        SubElement(console, "target", type="serial", port="0")

        # QEMU guest agent channel.
        channel = SubElement(devices, "channel", type="unix")
        SubElement(channel, "target", type="virtio", name="org.qemu.guest_agent.0")

        # Input devices.
        SubElement(devices, "input", type="tablet", bus="usb")
        SubElement(devices, "input", type="mouse", bus="ps2")
        SubElement(devices, "input", type="keyboard", bus="ps2")

        # Graphics.
        devices.append(self.graphics.xml())

        # Audio (none).
        SubElement(devices, "audio", id="1", type="none")

        # Video.
        video = SubElement(devices, "video")
        SubElement(video, "model", type="virtio", heads="1", primary="yes")

        # Misc.
        SubElement(devices, "watchdog", model="itco", action="reset")
        SubElement(devices, "memballoon", model="virtio")

        rng = SubElement(devices, "rng", model="virtio")
        SubElement(rng, "backend", model="random").text = "/dev/urandom"
