from __future__ import annotations

from pathlib import Path

import pytest

import eznet.jnpr.download  # noqa: F401 — registers device methods


pytestmark = pytest.mark.testbed


# ---------------------------------------------------------------------------
# download
# ---------------------------------------------------------------------------

class TestDownload:
    async def test_download_single_file(self, device, tmp_path):
        await device.download("/var/log/messages", local_path=tmp_path)
        downloaded = tmp_path / "hostname"
        assert downloaded.exists()
        assert downloaded.stat().st_size > 0

    async def test_download_string_path(self, device, tmp_path):
        await device.download("/var/log/messages", local_path=str(tmp_path))
        downloaded = tmp_path / "hostname"
        assert downloaded.exists()

    async def test_download_creates_local_dir(self, device, tmp_path):
        dest = tmp_path / "subdir" / "nested"
        await device.download("/var/log/messages", local_path=dest)
        assert dest.exists()
        assert (dest / "hostname").exists()

    async def test_download_re0(self, device, tmp_path):
        await device.download("/var/log/messages", local_path=tmp_path, re="re0")
        downloaded = tmp_path / "re0.hostname"
        assert downloaded.exists()
        assert downloaded.stat().st_size > 0

    async def test_download_path_object(self, device, tmp_path):
        await device.download(Path("/var/log/messages"), local_path=tmp_path)
        downloaded = tmp_path / "hostname"
        assert downloaded.exists()


# ---------------------------------------------------------------------------
# download_tar
# ---------------------------------------------------------------------------

class TestDownloadTar:
    async def test_download_tar_single_file(self, device, tmp_path):
        await device.download_tar("/var/log/messages", local_path=tmp_path)
        downloaded = tmp_path / "etc.hostname.tgz"
        assert downloaded.exists()
        assert downloaded.stat().st_size > 0

    async def test_download_tar_directory(self, device, tmp_path):
        await device.download_tar("/var/log/messages*", local_path=tmp_path)
        downloaded = tmp_path / "var.log.messages.tgz"
        assert downloaded.exists()
        assert downloaded.stat().st_size > 0

    async def test_download_tar_creates_local_dir(self, device, tmp_path):
        dest = tmp_path / "output"
        await device.download_tar("/var/log/messages", local_path=dest)
        assert dest.exists()
        assert (dest / "etc.hostname.tgz").exists()

    async def test_download_tar_re0(self, device, tmp_path):
        await device.download_tar("/var/log/messages", local_path=tmp_path, re="re0")
        downloaded = tmp_path / "re0.etc.hostname.tgz"
        assert downloaded.exists()
        assert downloaded.stat().st_size > 0
