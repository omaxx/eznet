import pytest

import os

from eznet import Device
from eznet.inventory.device.junos import CommandError

PROXY = "172.31.0.8"
VMX_1_IP = "172.31.0.96"
VMX_2_IP = "172.31.0.97"
VMX_1_RE_IP = "192.168.0.1"
VMX_1_RE0_IP = "192.168.0.10"
VMX_1_RE1_IP = "192.168.0.11"
VMX_2_RE_IP = "192.168.0.2"

USER = os.environ['USER']
ROOT_PASS = "Juniper#123"

@pytest.mark.asyncio
async def test_cmd():
    vmx_1 = Device(VMX_1_IP)

    async with vmx_1.ssh:
        await vmx_1.run_cmd("show system info")


@pytest.mark.asyncio
async def test_cmd_error():
    vmx_1 = Device(VMX_1_IP)

    async with vmx_1.ssh:
        with pytest.raises(CommandError):
            await vmx_1.run_cmd("show boo")


@pytest.mark.asyncio
async def test_shell_cmd():
    vmx_1 = Device(VMX_1_IP, root_pass=ROOT_PASS)

    async with vmx_1.ssh:
        assert USER in (await vmx_1.run_shell_cmd("id -un"))
        assert "R1" in (await vmx_1.run_shell_cmd("hostname"))

        assert "root" in (await vmx_1.run_shell_cmd("id -un", as_root=True))
        assert "R1_re0" in (await vmx_1.run_shell_cmd("hostname", as_root=True, re="re0"))
        assert "R1_re1" in (await vmx_1.run_shell_cmd("hostname", as_root=True, re="re1"))


@pytest.mark.asyncio
async def test_shell_cmd_error():
    vmx_1 = Device(VMX_1_IP, root_pass=ROOT_PASS)

    async with vmx_1.ssh:
        with pytest.raises(CommandError):
            assert USER in (await vmx_1.run_shell_cmd("boo"))


@pytest.mark.asyncio
async def test_pfe_cmd():
    vmx_1 = Device(VMX_1_IP, root_pass=ROOT_PASS)

    async with vmx_1.ssh:
        assert "VMX" in (await vmx_1.run_pfe_cmd("show version"))


@pytest.mark.asyncio
async def test_pfe_cmd_error():
    vmx_1 = Device(VMX_1_IP, root_pass=ROOT_PASS)

    async with vmx_1.ssh:
        with pytest.raises(CommandError):
            await vmx_1.run_pfe_cmd("show foo")


@pytest.mark.asyncio
async def test_xml_cmd():
    vmx_1 = Device(VMX_1_IP)

    async with vmx_1.ssh:
        await vmx_1.run_xml_cmd("show system info")


@pytest.mark.xfail(reason="Not implemented yet")
@pytest.mark.asyncio
async def test_xml_cmd_error():
    vmx_1 = Device(VMX_1_IP)

    async with vmx_1.ssh:
        with pytest.raises(CommandError):
            await vmx_1.run_xml_cmd("show isis interface")
        with pytest.raises(CommandError):
            await vmx_1.run_xml_cmd("show vrrp summary")

@pytest.mark.asyncio
async def test_json_cmd():
    vmx_1 = Device(VMX_1_IP)

    async with vmx_1.ssh:
        await vmx_1.run_json_cmd("show system info")


@pytest.mark.xfail(reason="Not implemented yet")
@pytest.mark.asyncio
async def test_json_cmd_error():
    vmx_1 = Device(VMX_1_IP)

    async with vmx_1.ssh:
        with pytest.raises(CommandError):
            await vmx_1.run_json_cmd("show isis interface")
        with pytest.raises(CommandError):
            await vmx_1.run_json_cmd("show vrrp summary")


@pytest.mark.asyncio
async def test_config():
    vmx_1 = Device(VMX_1_IP)

    async with vmx_1.ssh:
        await vmx_1.config("set system host-name TEST")
        assert "TEST" in (await vmx_1.run_cmd("show system information"))
        await vmx_1.config("del system host-name")
        assert "R1" in (await vmx_1.run_cmd("show system information"))
