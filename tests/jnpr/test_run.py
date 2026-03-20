from __future__ import annotations

from xml.etree import ElementTree

import pytest

from eznet.jnpr.run import CommandError
import eznet.jnpr.run  # noqa: F401 — registers device methods


pytestmark = pytest.mark.testbed


# ---------------------------------------------------------------------------
# cli_cmd
# ---------------------------------------------------------------------------

class TestCliCmd:
    async def test_show_version(self, device):
        output = await device.run_cli_cmd("show version")
        assert "Junos" in output or "JUNOS" in output

    async def test_show_hostname(self, device):
        output = await device.run_cli_cmd("show configuration system host-name")
        assert output.strip() != ""

    async def test_invalid_command(self, device):
        with pytest.raises(CommandError):
            await device.run_cli_cmd("show nonexistent_command_12345")


# ---------------------------------------------------------------------------
# shell_cmd
# ---------------------------------------------------------------------------

class TestShellCmd:
    async def test_uname(self, device):
        output = await device.run_shell_cmd("uname -s")
        assert output.strip() != ""

    async def test_ls(self, device):
        output = await device.run_shell_cmd("ls /")
        assert "var" in output

    async def test_whoami(self, device):
        output = await device.run_shell_cmd("whoami")
        assert output.strip() != ""


# ---------------------------------------------------------------------------
# re_cmd
# ---------------------------------------------------------------------------

class TestReCmd:
    async def test_re_local(self, dual_re_device):
        output = await dual_re_device.run_re_cmd("uname -n", re="local")
        assert output.strip() != ""

    async def test_re_master_cli(self, dual_re_device):
        output = await dual_re_device.run_re_cmd("show version", re="master", cli=True)
        assert output.strip() != ""


# ---------------------------------------------------------------------------
# xml_cmd
# ---------------------------------------------------------------------------

class TestXmlCmd:
    async def test_show_version_xml(self, device):
        xml = await device.run_xml_cmd("show version")
        assert isinstance(xml, ElementTree.Element)

    async def test_show_interfaces_xml(self, device):
        xml = await device.run_xml_cmd("show interfaces terse")
        assert isinstance(xml, ElementTree.Element)
        assert len(xml) > 0


# ---------------------------------------------------------------------------
# json_cmd
# ---------------------------------------------------------------------------

class TestJsonCmd:
    async def test_show_version_json(self, device):
        data = await device.run_json_cmd("show version")
        assert isinstance(data, dict)
        assert len(data) > 0

    async def test_show_interfaces_json(self, device):
        data = await device.run_json_cmd("show interfaces terse")
        assert isinstance(data, dict)
