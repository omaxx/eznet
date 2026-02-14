from __future__ import annotations

from dataclasses import dataclass
from typing import ParamSpec, TypeVar, Callable, Coroutine, Any
import asyncio
import functools
import logging
from pathlib import Path

import libvirt

from eznet.drivers.ssh import SSH

TCP_URI = "qemu+tcp://127.0.0.1:{port}/system"
LIBVIRT_PORT = 16509
SOCK_URI = "qemu+unix:///system?socket={socket}"
LIBVIRT_SOCK = "/var/run/libvirt/libvirt-sock"

P = ParamSpec("P")
T = TypeVar("T")

logger = logging.getLogger(__name__)


def sync_to_async(
    method: Callable[P, T]
) -> Callable[P, Coroutine[Any, Any, T]]:
    @functools.wraps(method)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return await asyncio.to_thread(method, *args, **kwargs)
    return wrapper


@dataclass
class VM:
    name: str
    active: bool


@dataclass
class VNet:
    name: str
    active: bool


class Qemu:
    def __init__(
        self,
        ssh: SSH,
    ):
        self._ssh = ssh

        self._port: int | None = None
        self._socket: Path | None = None
        self._virt: libvirt.virConnect | None = None

    async def __aenter__(self):
        await self.open()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def open(self):
        await self._ssh.open()
        try:
            # self._port = await self._ssh.forward_local_port(port=LIBVIRT_PORT)
            self._socket = await self._ssh.forward_local_path(path=LIBVIRT_SOCK)
        except:
            await self._ssh.close()
            raise
        def sync():
            # self._virt = libvirt.open(TCP_URI.format(port=self._port))
            self._virt = libvirt.open(SOCK_URI.format(socket=self._socket))
        try:
            await asyncio.to_thread(sync)
        except:
            # await self._ssh.close_forwarding(self._port)
            # self._port = None
            await self._ssh.close_forwarding(self._socket)
            self._socket = None
            await self._ssh.close()
            raise

    async def close(self):
        def sync():
            self._virt.close()
        await asyncio.to_thread(sync)
        # await self._ssh.close_forwarding(self._port)
        # self._port = None
        await self._ssh.close_forwarding(self._socket)
        self._socket = None
        await self._ssh.close()

    @sync_to_async
    def define_vm(self, name: str, xml: str) -> None:
        for vm in self._virt.listAllDomains():
            if vm.name() == name:
                logger.error(f"VM `{name}` already defined")
                break
        else:
            self._virt.defineXML(xml)
            logger.info(f"VM `{name}` defined")

    @sync_to_async
    def define_vnet(self, name: str, xml: str) -> None:
        for vnet in self._virt.listAllNetworks():
            if vnet.name() == name:
                logger.error(f"VNet `{name}` already defined")
                break
        else:
            self._virt.networkDefineXML(xml)
            logger.info(f"Vnet `{name}` defined")

    @sync_to_async
    def start_vm(self, name: str) -> None:
        for vm in self._virt.listAllDomains():
            if vm.name() == name:
                if not vm.isActive():
                    vm.create()
                    logger.info(f"VM `{name}` started")
                else:
                    logger.warning(f"VM `{name}` already started")
                break
        else:
            logger.error(f"VM `{name}` not found")

    @sync_to_async
    def start_vnet(self, name: str) -> None:
        for vnet in self._virt.listAllNetworks():
            if vnet.name() == name:
                if not vnet.isActive():
                    vnet.create()
                    logger.info(f"Vnet `{name}` started")
                else:
                    logger.warning(f"Vnet `{name}` already started")
                break
        else:
            logger.error(f"Vnet `{name}` not found")

    @sync_to_async
    def stop_vm(self, name: str) -> None:
        for vm in self._virt.listAllDomains():
            if vm.name() == name:
                if vm.isActive():
                    vm.destroy()
                    logger.info(f"VM `{name}` stopped")
                else:
                    logger.warning(f"VM `{name}` already stopped")
                break
        else:
            logger.error(f"VM `{name}` not found")

    @sync_to_async
    def stop_vnet(self, name: str) -> None:
        for vnet in self._virt.listAllNetworks():
            if vnet.name() == name:
                if vnet.isActive():
                    vnet.destroy()
                    logger.info(f"Vnet `{name}` stopped")
                else:
                    logger.warning(f"Vnet `{name}` already stopped")
                break
        else:
            logger.error(f"Vnet `{name}` not found")

    @sync_to_async
    def undefine_vm(self, name: str) -> None:
        for vm in self._virt.listAllDomains():
            if vm.name() == name:
                if vm.isActive():
                    logger.warning(f"VM `{name}` is running, stopping first")
                    vm.destroy()
                    logger.info(f"VM `{name}` stopped")
                vm.undefine()
                logger.info(f"VM `{name}` undefined")
                break
        else:
            logger.warning(f"VM `{name}` not found")

    @sync_to_async
    def undefine_vnet(self, name: str) -> None:
        for vnet in self._virt.listAllNetworks():
            if vnet.name() == name:
                if vnet.isActive():
                    logger.warning(f"VNet `{name}` is running, stopping first")
                    vnet.destroy()
                    logger.info(f"Vnet `{name}` stopped")
                vnet.undefine()
                logger.info(f"Vnet `{name}` undefined")
                break
        else:
            logger.warning(f"Vnet `{name}` not found")


    async def list_vms(self) -> list[VM]:
        def sync():
            return [
                VM(
                    name=domain.name(),
                    active=domain.isActive()
                )
                for domain in self._virt.listAllDomains()
            ]
        return await asyncio.to_thread(sync)

    async def list_vnets(self) -> list[VNet]:
        def sync():
            return [
                VNet(
                    name=network.name(),
                    active=network.isActive(),
                )
                for network in self._virt.listAllNetworks()
            ]
        return await asyncio.to_thread(sync)
