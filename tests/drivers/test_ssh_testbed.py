from __future__ import annotations

import pytest

from eznet.drivers.ssh import SSH, State


pytestmark = pytest.mark.testbed


class TestSSHConnection:
    async def test_connect(self, device_info):
        ssh = SSH(name=device_info["name"], ip=device_info["ip"])
        await ssh.open()
        assert ssh.state == State.CONNECTED
        assert ssh.connection is not None
        await ssh.close()
        assert ssh.opened == 0

    async def test_context_manager(self, device_info):
        ssh = SSH(name=device_info["name"], ip=device_info["ip"])
        async with ssh:
            assert ssh.state == State.CONNECTED


class TestSSHRun:
    async def test_run_command(self, ssh):
        result = await ssh.run("uname -a")
        assert result.stdout.strip() != ""

    async def test_run_multiple_commands(self, ssh, device_info):
        r1 = await ssh.run("uname -a")
        r2 = await ssh.run("hostname")
        assert device_info["name"] in r1.stdout
        assert device_info["name"] in r2.stdout

    async def test_run_stderr(self, ssh):
        result = await ssh.run("nonexistent_command", timeout=10)
        assert result.stderr != "" or result.exit_code != 0


class TestSSHFileTransfer:
    async def test_download(self, ssh, tmp_path):
        result = await ssh.download("/var/log/README", str(tmp_path))
        assert len(result) > 0

    async def test_upload_and_download(self, ssh, tmp_path):
        upload_file = tmp_path / "test_upload.txt"
        upload_file.write_text("testbed upload test")

        await ssh.upload(str(upload_file), "/tmp/")

        download_dir = tmp_path / "downloaded"
        download_dir.mkdir()
        await ssh.download("/tmp/test_upload.txt", str(download_dir))

        downloaded = download_dir / "test_upload.txt"
        assert downloaded.exists()
        assert downloaded.read_text() == "testbed upload test"

        await ssh.run("start shell command \"rm /tmp/test_upload.txt\"")
