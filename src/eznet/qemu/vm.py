from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring, indent, register_namespace

VLAB_NS = "http://eznet/vlab/1.0"
register_namespace("vlab", VLAB_NS)

@dataclass
class Disk:
    path: Path
    target: str
    format: Literal["qcow2", "raw"] = "qcow2"
    bus: Literal["virtio", "scsi", "sata", "ide", "usb"] = "virtio"
    device: Literal["disk", "cdrom"] = "disk"
    snapshot: bool = False

    def xml(self, path: Path) -> Element:
        elem = Element("disk", type="file", device=self.device)
        SubElement(elem, "driver", name="qemu", type=self.format)
        SubElement(elem, "source", file=str(path / self.path.name))
        SubElement(elem, "target", dev=self.target, bus=self.bus)
        return elem


@dataclass
class Interface:
    type: Literal["network", "bridge", "udp"]
    source: str
    target: str | None = None
    mac: str | None = None
    model: Literal["virtio", "e1000", "rtl8139"] = "virtio"

    def xml(self) -> Element:
        elem = Element("interface", type=self.type)

        if self.mac is not None:
            SubElement(elem, "mac", address=self.mac)

        if self.type == "network":
            SubElement(elem, "source", network=self.source)
            if self.target is not None:
                SubElement(elem, "target", dev=self.target)

        elif self.type == "bridge":
            SubElement(elem, "source", bridge=self.source)
            if self.target is not None:
                SubElement(elem, "target", dev=self.target)

        elif self.type == "udp":
            remote_addr, remote_port = self.source.rsplit(":", 1)
            local_addr, local_port = self.target.rsplit(":", 1)
            source_elem = SubElement(
                elem, "source",
                address=remote_addr,
                port=remote_port,
            )
            SubElement(
                source_elem, "local",
                address=local_addr,
                port=local_port,
            )

        SubElement(elem, "model", type=self.model)
        return elem


@dataclass
class Graphics:
    type: Literal["vnc", "spice"] = "vnc"
    port: int = -1
    listen: str = "127.0.0.1"

    def xml(self) -> Element:
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
    name: str
    path: Path
    vcpus: int = 1
    memory_mb: int = 1024
    disks: list[Disk] = field(default_factory=list)
    interfaces: list[Interface] = field(default_factory=list)
    graphics: Graphics = field(default_factory=Graphics)
    arch: Literal["x86_64", "aarch64"] = "x86_64"
    machine: str = "q35"
    cpu_mode: Literal[
        "host-passthrough", "host-model", "custom"
    ] = "host-passthrough"
    emulator: str = "/usr/bin/qemu-system-x86_64"

    def xml(self) -> str:
        root = self._build_domain()
        indent(root, space="  ")
        return tostring(root, encoding="unicode", xml_declaration=False)

    def _build_domain(self) -> Element:
        domain = Element("domain", type="kvm")

        SubElement(domain, "name").text = self.name

        SubElement(domain, "memory", unit="MiB").text = str(self.memory_mb)
        SubElement(domain, "vcpu", placement="static").text = str(self.vcpus)

        self._build_os(domain)
        self._build_features(domain)
        self._build_cpu(domain)
        self._build_clock(domain)
        self._build_power(domain)
        self._build_devices(domain)

        return domain

    def _build_os(self, parent: Element) -> None:
        os_elem = SubElement(parent, "os")
        os_type = SubElement(os_elem, "type", arch=self.arch, machine=self.machine)
        os_type.text = "hvm"
        SubElement(os_elem, "boot", dev="hd")

    def _build_features(self, parent: Element) -> None:
        features = SubElement(parent, "features")
        SubElement(features, "acpi")
        SubElement(features, "apic")

    def _build_cpu(self, parent: Element) -> None:
        SubElement(
            parent, "cpu",
            mode=self.cpu_mode, check="none", migratable="on",
        )

    def _build_clock(self, parent: Element) -> None:
        clock = SubElement(parent, "clock", offset="utc")
        SubElement(clock, "timer", name="rtc", tickpolicy="catchup")
        SubElement(clock, "timer", name="pit", tickpolicy="delay")
        SubElement(clock, "timer", name="hpet", present="no")

    def _build_power(self, parent: Element) -> None:
        SubElement(parent, "on_poweroff").text = "destroy"
        SubElement(parent, "on_reboot").text = "restart"
        SubElement(parent, "on_crash").text = "destroy"

        pm = SubElement(parent, "pm")
        SubElement(pm, "suspend-to-mem", enabled="no")
        SubElement(pm, "suspend-to-disk", enabled="no")

    def _build_devices(self, parent: Element) -> None:
        devices = SubElement(parent, "devices")

        SubElement(devices, "emulator").text = self.emulator

        for disk in self.disks:
            devices.append(disk.xml(path=self.path))

        for iface in self.interfaces:
            devices.append(iface.xml())

        serial = SubElement(devices, "serial", type="pty")
        target = SubElement(serial, "target", type="isa-serial", port="0")
        SubElement(target, "model", name="isa-serial")

        console = SubElement(devices, "console", type="pty")
        SubElement(console, "target", type="serial", port="0")

        channel = SubElement(devices, "channel", type="unix")
        SubElement(channel, "target", type="virtio", name="org.qemu.guest_agent.0")

        SubElement(devices, "input", type="tablet", bus="usb")
        SubElement(devices, "input", type="mouse", bus="ps2")
        SubElement(devices, "input", type="keyboard", bus="ps2")

        devices.append(self.graphics.xml())

        SubElement(devices, "audio", id="1", type="none")

        video = SubElement(devices, "video")
        SubElement(video, "model", type="virtio", heads="1", primary="yes")

        # SubElement(devices, "watchdog", model="itco", action="reset")
        SubElement(devices, "memballoon", model="virtio")

        rng = SubElement(devices, "rng", model="virtio")
        SubElement(rng, "backend", model="random").text = "/dev/urandom"
