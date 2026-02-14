"""Virtual lab management — deploy and manage VMs on a remote KVM host."""

from __future__ import annotations

import logging
from pathlib import Path

from eznet.host import Host
from eznet.vlab.templates import Template


DEFAULT_BASE_PATH = "/var/vlab"
DEFAULT_IMAGES_DIR = "images"
DEFAULT_VMS_DIR = "vms"


class VLab:
    """Deploys and manages devices on a remote KVM host.

    A device is defined by a ``Template`` and may consist of one or
    more VMs. VLab handles directory creation, image provisioning,
    initial configuration, and libvirt domain definition.

    Directory layout::

        {base_path}/
        ├── images/          # shared base images
        └── vms/
            └── {device}/    # one directory per device
                ├── {vm-1}/  # subfolder per VM (multi-VM devices)
                └── {vm-2}/

    For single-VM devices the device directory is the VM directory
    (no extra nesting).

    Args:
        host: Remote KVM host to deploy on.
        base_path: Root directory for all vlab data on the host.
    """

    def __init__(
        self,
        host: Host,
        base_path: str = DEFAULT_BASE_PATH,
    ) -> None:
        self.host = host
        self.base_path = Path(base_path)
        self.images_path = self.base_path / DEFAULT_IMAGES_DIR
        self.vms_path = self.base_path / DEFAULT_VMS_DIR
        self.logger = logging.getLogger(f"{__name__}.{host.name}")

    async def copy(
        self,
        src: str | Path,
        dst: str | Path,
        force: bool = False,
    ) -> None:
        """Copies a file on the remote host.

        Args:
            src: Source file path.
            dst: Destination file path.
            force: If True, overwrite existing file.
        """
        test = f"test -e {dst}" if not force else "false"
        await self.host.run(f"{test} || rsync -a {src} {dst}")

    async def make_snapshot(
        self,
        src: str | Path,
        dst: str | Path,
        force: bool = False,
    ) -> None:
        """Creates a qcow2 snapshot backed by the source image.

        Args:
            src: Backing file path.
            dst: Destination overlay file path.
            force: If True, overwrite existing file.
        """
        test = f"test -e {dst}" if not force else "false"
        await self.host.run(
            f"{test} || qemu-img create -f qcow2 -b {src} -F qcow2 {dst}"
        )

    async def create(self, template: Template) -> None:
        """Deploys a device from a template.

        Steps for each VM in the template:
            1. Create the device directory (and VM subdirectory if multi-VM).
            2. Provision disk images (copy or snapshot).
            3. Write initial configuration files and run init commands.
            4. Define the VM in libvirt.

        Args:
            template: Device template describing one or more VMs.
        """
        device_path = self.vms_path / template.name
        vm_names = template.vm_names()
        multi_vm = len(vm_names) > 1

        self.logger.info(f"Creating device `{template.name}`")
        await self.host.mkdir(device_path)

        for vm_name in vm_names:
            # Single-VM: device dir is the VM dir.
            # Multi-VM: each VM gets a subfolder.
            if multi_vm:
                vm_path = device_path / vm_name
                await self.host.mkdir(vm_path)
            else:
                vm_path = device_path

            self.logger.info(f"Deploying VM `{vm_name}`")

            # 1. Provision images.
            for img in template.images(vm_name):
                src = self.images_path / img.source
                dst = vm_path / img.filename
                self.logger.info(
                    f"Provisioning image `{img.source}` ({img.mode})"
                )
                if img.mode == "copy":
                    await self.copy(src, dst)
                else:
                    await self.make_snapshot(src, dst)

            # 2. Initial configuration.
            init = template.init(vm_name, str(vm_path))
            for filename, content in init.files.items():
                await self.host.write_file(vm_path / filename, content)
            for cmd in init.commands:
                await self.host.run(cmd)

            # 3. Define VM in libvirt.
            domain = template.domain(vm_name, str(vm_path))
            self.logger.info(f"Defining VM `{vm_name}` in libvirt")
            await self.host.qemu.define_vm(vm_name, domain.xml())

            self.logger.info(f"VM `{vm_name}` created")

        self.logger.info(f"Device `{template.name}` created")