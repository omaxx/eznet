from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import asyncssh
import pytest

from eznet.drivers.ssh import (
    SSH,
    CmdExec,
    FileTransfer,
    Semaphore,
    Settings,
    State,
    create_client_factory,
    create_session_factory,
    get_free_port,
    get_temp_file,
    semaphore,
    settings,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def ssh():
    return SSH(name="test-device", ip="10.0.0.1", user_name="admin", user_pass="secret")


@pytest.fixture
def ssh_with_proxy():
    proxy = SSH(name="proxy", ip="10.0.0.254", user_name="admin")
    return SSH(name="test-device", ip="10.0.0.1", user_name="admin", proxy=proxy)


@pytest.fixture
def connected_ssh(ssh):
    """SSH instance with a mocked connection."""
    ssh.connection = AsyncMock(spec=asyncssh.SSHClientConnection)
    ssh.state = State.CONNECTED
    return ssh


# ---------------------------------------------------------------------------
# CmdExec
# ---------------------------------------------------------------------------

class TestCmdExec:
    def test_init(self):
        cmd = CmdExec("show version")
        assert cmd.cmd == "show version"
        assert cmd.stdout == ""
        assert cmd.stderr == ""
        assert cmd.exit_code is None

    def test_stdout_decoding(self):
        cmd = CmdExec("test")
        cmd.stdout_bytes += b"hello world"
        assert cmd.stdout == "hello world"

    def test_stderr_decoding(self):
        cmd = CmdExec("test")
        cmd.stderr_bytes += b"error message"
        assert cmd.stderr == "error message"

    def test_bool_success(self):
        cmd = CmdExec("test")
        cmd.exit_code = 0
        assert bool(cmd) is True

    def test_bool_failure(self):
        cmd = CmdExec("test")
        cmd.exit_code = 1
        assert bool(cmd) is False

    def test_bool_none(self):
        cmd = CmdExec("test")
        assert bool(cmd) is False


# ---------------------------------------------------------------------------
# FileTransfer
# ---------------------------------------------------------------------------

class TestFileTransfer:
    def test_init(self):
        ft = FileTransfer("test.tgz")
        assert ft.file_name == "test.tgz"
        assert ft.received_bytes == 0
        assert ft.total_bytes == 0
        assert ft.speed == 0

    def test_repr_zero_total(self):
        ft = FileTransfer("test.tgz")
        r = repr(ft)
        assert "test.tgz" in r
        assert "100%" in r

    def test_repr_with_progress(self):
        ft = FileTransfer("test.tgz")
        ft.received_bytes = 500
        ft.total_bytes = 1000
        ft.speed = 100
        r = repr(ft)
        assert "50%" in r
        assert "100 Bps" in r


# ---------------------------------------------------------------------------
# SSH init and str
# ---------------------------------------------------------------------------

class TestSSHInit:
    def test_defaults(self, ssh):
        assert ssh.name == "test-device"
        assert ssh.ip == "10.0.0.1"
        assert str(ssh) == "test-device@10.0.0.1"
        assert ssh.state == State.DISCONNECTED
        assert ssh.connection is None
        assert ssh.opened == 0
        assert ssh.executions == []
        assert ssh.error is None

    def test_no_ip_uses_name(self):
        s = SSH(name="router1")
        assert s.ip == "router1"
        assert str(s) == "router1"

    def test_with_proxy(self, ssh_with_proxy):
        assert ssh_with_proxy.proxy is not None
        assert ssh_with_proxy.proxy.name == "proxy"


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class TestState:
    def test_repr(self):
        assert repr(State.CONNECTED) == "CONNECTED"

    def test_str(self):
        assert str(State.DISCONNECTED) == "DISCONNECTED"


# ---------------------------------------------------------------------------
# Semaphore
# ---------------------------------------------------------------------------

class TestSemaphore:
    async def test_connection_semaphore(self):
        s = Semaphore()
        sem = s.connection
        assert isinstance(sem, asyncio.Semaphore)

    async def test_download_semaphore(self):
        s = Semaphore()
        sem = s.download
        assert isinstance(sem, asyncio.Semaphore)

    async def test_upload_semaphore(self):
        s = Semaphore()
        sem = s.upload
        assert isinstance(sem, asyncio.Semaphore)

    async def test_same_loop_returns_same_semaphore(self):
        s = Semaphore()
        assert s.connection is s.connection


# ---------------------------------------------------------------------------
# SSH open / close
# ---------------------------------------------------------------------------

class TestSSHOpenClose:
    async def test_open_increments_opened(self, ssh):
        with patch.object(ssh, "connect", new_callable=AsyncMock):
            await ssh.open()
            assert ssh.opened == 1
            await ssh.open()
            assert ssh.opened == 2

    async def test_close_decrements_opened(self, ssh):
        ssh.opened = 2
        with patch.object(ssh, "disconnect", new_callable=AsyncMock):
            await ssh.close()
            assert ssh.opened == 1

    async def test_close_disconnects_at_zero(self, ssh):
        ssh.opened = 1
        with patch.object(ssh, "disconnect", new_callable=AsyncMock) as mock_disconnect:
            await ssh.close()
            assert ssh.opened == 0
            mock_disconnect.assert_awaited_once()

    async def test_open_with_proxy(self, ssh_with_proxy):
        with (
            patch.object(ssh_with_proxy, "connect", new_callable=AsyncMock),
            patch.object(ssh_with_proxy.proxy, "open", new_callable=AsyncMock) as mock_proxy_open,
        ):
            await ssh_with_proxy.open()
            mock_proxy_open.assert_awaited_once()

    async def test_open_closes_proxy_on_connect_failure(self, ssh_with_proxy):
        with (
            patch.object(ssh_with_proxy, "connect", new_callable=AsyncMock, side_effect=ConnectionError),
            patch.object(ssh_with_proxy.proxy, "open", new_callable=AsyncMock),
            patch.object(ssh_with_proxy.proxy, "close", new_callable=AsyncMock) as mock_proxy_close,
        ):
            with pytest.raises(ConnectionError):
                await ssh_with_proxy.open()
            mock_proxy_close.assert_awaited_once()

    async def test_context_manager(self, ssh):
        with (
            patch.object(ssh, "open", new_callable=AsyncMock) as mock_open,
            patch.object(ssh, "close", new_callable=AsyncMock) as mock_close,
        ):
            async with ssh:
                mock_open.assert_awaited_once()
            mock_close.assert_awaited_once()


# ---------------------------------------------------------------------------
# SSH connect
# ---------------------------------------------------------------------------

class TestSSHConnect:
    async def test_connect_already_connected(self, connected_ssh):
        """Should return immediately if already connected."""
        original_connection = connected_ssh.connection
        await connected_ssh.connect()
        assert connected_ssh.connection is original_connection

    @patch("eznet.drivers.ssh.asyncssh.connect", new_callable=AsyncMock)
    @patch("eznet.drivers.ssh.create_client_factory")
    async def test_connect_success(self, mock_factory, mock_connect, ssh):
        mock_conn = AsyncMock(spec=asyncssh.SSHClientConnection)
        mock_connect.return_value = mock_conn

        await ssh.connect()

        assert ssh.connection is mock_conn
        assert ssh.state == State.CONNECTED
        assert ssh.error is None

    @patch("eznet.drivers.ssh.asyncssh.connect", new_callable=AsyncMock)
    async def test_connect_permission_denied(self, mock_connect, ssh):
        mock_connect.side_effect = asyncssh.PermissionDenied("denied")

        with pytest.raises(asyncssh.PermissionDenied):
            await ssh.connect()

        assert ssh.state == State.DISCONNECTED
        assert ssh.error == "PermissionDenied"
        assert ssh.connection is None

    @patch("eznet.drivers.ssh.asyncssh.connect", new_callable=AsyncMock)
    async def test_connect_timeout(self, mock_connect, ssh):
        mock_connect.side_effect = TimeoutError("timed out")

        with pytest.raises(TimeoutError):
            await ssh.connect()

        assert ssh.state == State.DISCONNECTED
        assert ssh.error == "TimeoutError"


# ---------------------------------------------------------------------------
# SSH disconnect
# ---------------------------------------------------------------------------

class TestSSHDisconnect:
    async def test_disconnect_when_connected(self, connected_ssh):
        await connected_ssh.disconnect()
        connected_ssh.connection.close.assert_called_once()
        connected_ssh.connection.wait_closed.assert_awaited_once()

    async def test_disconnect_when_not_connected(self, ssh):
        await ssh.disconnect()  # should not raise


# ---------------------------------------------------------------------------
# SSH run
# ---------------------------------------------------------------------------

class TestSSHRun:
    async def test_run_not_connected_asserts(self, ssh):
        with pytest.raises(AssertionError):
            await ssh.run("show version")

    async def test_run_success(self, connected_ssh):
        mock_chan = AsyncMock()
        mock_chan.wait_closed = AsyncMock()
        mock_session = MagicMock()

        connected_ssh.connection.create_session = AsyncMock(
            return_value=(mock_chan, mock_session)
        )

        result = await connected_ssh.run("show version", timeout=5)

        assert isinstance(result, CmdExec)
        assert result.cmd == "show version"
        assert connected_ssh.executions == []  # cleaned up after success

    async def test_run_with_stdin(self, connected_ssh):
        mock_chan = MagicMock()
        mock_chan.wait_closed = AsyncMock()

        connected_ssh.connection.create_session = AsyncMock(
            return_value=(mock_chan, MagicMock())
        )

        await connected_ssh.run("command", stdin="password123", timeout=5)
        mock_chan.write.assert_called_once()
        mock_chan.write_eof.assert_called_once()

    async def test_run_timeout(self, connected_ssh):
        mock_chan = AsyncMock()
        mock_chan.wait_closed = AsyncMock(side_effect=asyncio.TimeoutError)

        connected_ssh.connection.create_session = AsyncMock(
            return_value=(mock_chan, MagicMock())
        )

        with pytest.raises(asyncio.TimeoutError):
            await connected_ssh.run("slow command", timeout=1)


# ---------------------------------------------------------------------------
# create_client_factory
# ---------------------------------------------------------------------------

class TestCreateClientFactory:
    async def test_connection_lost_no_error(self, connected_ssh):
        # Acquire semaphore first so release() doesn't over-release
        await semaphore.connection.acquire()

        factory = create_client_factory(connected_ssh)
        client = factory()
        client.connection_lost(None)

        assert connected_ssh.connection is None
        assert connected_ssh.state == State.DISCONNECTED

    async def test_connection_lost_with_error(self, connected_ssh):
        await semaphore.connection.acquire()

        factory = create_client_factory(connected_ssh)
        client = factory()
        client.connection_lost(OSError("connection reset"))

        assert connected_ssh.connection is None
        assert connected_ssh.state == State.DISCONNECTED
        assert connected_ssh.error == "OSError"

    async def test_connection_lost_guard_prevents_double_release(self, connected_ssh):
        await semaphore.connection.acquire()

        factory = create_client_factory(connected_ssh)
        client = factory()

        # First call clears connection
        client.connection_lost(None)
        assert connected_ssh.connection is None

        # Second call should be a no-op (guard)
        client.connection_lost(None)  # should not raise


# ---------------------------------------------------------------------------
# create_session_factory
# ---------------------------------------------------------------------------

class TestCreateSessionFactory:
    def test_data_received_stdout(self, connected_ssh):
        execution = CmdExec("test")
        factory = create_session_factory(connected_ssh, execution)
        session = factory()

        session.data_received(b"hello", None)
        assert execution.stdout_bytes == b"hello"

    def test_data_received_stderr(self, connected_ssh):
        execution = CmdExec("test")
        factory = create_session_factory(connected_ssh, execution)
        session = factory()

        session.data_received(b"error", asyncssh.EXTENDED_DATA_STDERR)
        assert execution.stderr_bytes == b"error"

    def test_exit_status_received(self, connected_ssh):
        execution = CmdExec("test")
        factory = create_session_factory(connected_ssh, execution)
        session = factory()

        session.exit_status_received(0)
        assert execution.exit_code == 0

    def test_callbacks_invoked(self, connected_ssh):
        execution = CmdExec("test")
        stdout_cb = MagicMock()
        stderr_cb = MagicMock()

        factory = create_session_factory(
            connected_ssh, execution,
            stdout_received_callback=stdout_cb,
            stderr_received_callback=stderr_cb,
        )
        session = factory()

        session.data_received(b"out", None)
        session.data_received(b"err", asyncssh.EXTENDED_DATA_STDERR)

        stdout_cb.assert_called_once_with(b"out")
        stderr_cb.assert_called_once_with(b"err")


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

class TestUtils:
    def test_get_free_port(self):
        port = get_free_port()
        assert isinstance(port, int)
        assert port > 0

    def test_get_free_port_unique(self):
        ports = {get_free_port() for _ in range(5)}
        # Ports should generally be unique (not guaranteed but very likely)
        assert len(ports) >= 2

    def test_get_temp_file(self):
        path = get_temp_file()
        assert isinstance(path, Path)
        assert path.name == "sock"
        assert path.parent.exists()
        # cleanup
        path.parent.rmdir()


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class TestSettings:
    def test_defaults(self):
        assert settings.DEFAULT_KEEPALIVE == 5
        assert settings.DEFAULT_CONNECT_TIMEOUT == 30
        assert settings.DEFAULT_CMD_TIMEOUT == 180
        assert settings.DEFAULT_ENCODING == "latin-1"
        assert settings.MAX_SIMULTANEOUS_CONNECTIONS == 64
        assert settings.MAX_SIMULTANEOUS_DOWNLOADS == 2
        assert settings.MAX_SIMULTANEOUS_UPLOADS == 2
        assert settings.MAX_DEVICE_SIMULTANEOUS_EXECUTIONS == 2
