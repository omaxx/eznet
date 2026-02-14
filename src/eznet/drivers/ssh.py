from __future__ import annotations

import os
import socket
import tempfile
from pathlib import Path
from enum import Enum, auto
from dataclasses import dataclass
import logging
import asyncio
from collections import defaultdict
from time import time
from typing import Callable

import asyncssh

from eznet.utils import Singleton


@dataclass
class Settings(Singleton):
    DEFAULT_KEEPALIVE: int = 5
    DEFAULT_CONNECT_TIMEOUT: int = 30
    DEFAULT_CMD_TIMEOUT: int = 180
    LONG_REQUEST_LOG_TIMEOUT: int = 10
    DEFAULT_ENCODING: str = "latin-1"

    MAX_SIMULTANEOUS_CONNECTIONS: int = 64
    MAX_SIMULTANEOUS_DOWNLOADS: int = 2
    MAX_SIMULTANEOUS_UPLOADS: int = 2
    MAX_DEVICE_SIMULTANEOUS_EXECUTIONS: int = 2


settings = Settings()

class State(Enum):
    DISCONNECTED = auto()
    PENDING_CONNECT = auto()
    CONNECTING = auto()
    CONNECTED = auto()

    def __repr__(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.name


class CmdExec:
    def __init__(self, cmd: str):
        self.cmd = cmd
        self.stdout_bytes = bytearray()
        self.stderr_bytes = bytearray()
        self.exit_code: int | None = None

    @property
    def stdout(self) -> str:
        return self.stdout_bytes.decode(encoding=settings.DEFAULT_ENCODING, errors="ignore")

    @property
    def stderr(self) -> str:
        return self.stderr_bytes.decode(encoding=settings.DEFAULT_ENCODING, errors="ignore")

    def __bool__(self) -> bool:
        return self.exit_code == 0


class Semaphore:
    def __init__(self):
        self._connection: dict[asyncio.AbstractEventLoop, asyncio.Semaphore] = defaultdict(
            lambda: asyncio.Semaphore(settings.MAX_SIMULTANEOUS_CONNECTIONS)
        )
        self._download: dict[asyncio.AbstractEventLoop, asyncio.Semaphore] = defaultdict(
            lambda: asyncio.Semaphore(settings.MAX_SIMULTANEOUS_DOWNLOADS)
        )
        self._upload: dict[asyncio.AbstractEventLoop, asyncio.Semaphore] = defaultdict(
            lambda: asyncio.Semaphore(settings.MAX_SIMULTANEOUS_UPLOADS)
        )

    @property
    def connection(self) -> asyncio.Semaphore:
        return self._connection[asyncio.get_running_loop()]

    @property
    def download(self) -> asyncio.Semaphore:
        return self._download[asyncio.get_running_loop()]

    @property
    def upload(self) -> asyncio.Semaphore:
        return self._upload[asyncio.get_running_loop()]


semaphore = Semaphore()


class SSH:
    def __init__(
        self,
        name: str,
        ip: str | None = None,
        user_name: str | None = None,
        user_pass: str | None = None,
        proxy: SSH | None = None,
        logger: logging.Logger | None = None,
    ):
        self.name = name
        if ip is None:
            self.str = self.name
        else:
            self.str = f"{name}@{ip}"
        self.ip = ip or name
        self.user_name = user_name
        self.user_pass = user_pass
        self.proxy = proxy
        self.logger: logging.Logger = logger or logging.getLogger(__name__)

        self.opened = 0
        self.connection: asyncssh.SSHClientConnection | None = None
        self.state: State = State.DISCONNECTED
        self.error: str | None = None
        self.executions: list[CmdExec] = []
        self._connect_lock: dict[asyncio.AbstractEventLoop, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._execute_semaphore: dict[asyncio.AbstractEventLoop, asyncio.Semaphore] = defaultdict(
            lambda: asyncio.Semaphore(settings.MAX_DEVICE_SIMULTANEOUS_EXECUTIONS)
        )
        self.forwarders: dict[int | Path, asyncssh.SSHListener] = {}

    @property
    def connect_lock(self) -> asyncio.Lock:
        return self._connect_lock[asyncio.get_running_loop()]

    @property
    def execute_semaphore(self) -> asyncio.Semaphore:
        return self._execute_semaphore[asyncio.get_running_loop()]

    def __str__(self) -> str:
        return self.str

    async def __aenter__(self):
        await self.open()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def open(self) -> None:
        if self.opened == 0:
            if self.proxy is not None:
                await self.proxy.open()
            try:
                await self.connect()
            except:
                if self.proxy is not None:
                    await self.proxy.close()
                raise
        self.opened += 1

    async def close(self) -> None:
        if self.opened == 1:
            await self.disconnect()
            if self.proxy is not None:
                await self.proxy.close()
        self.opened -= 1

    async def connect(self):
        async with self.connect_lock:
            if self.connection is not None:
                return

            self.error = None
            initial_state = self.state
            if semaphore.connection._value == 0:
                self.state = State.PENDING_CONNECT
                self.logger.info(f"{self}: {self.state}")

            await semaphore.connection.acquire()
            self.state = State.CONNECTING

            try:
                tunnel: asyncssh.SSHClientConnection | None = None
                if self.proxy is not None:
                    tunnel = self.proxy.connection
                    if tunnel is None:
                        raise ConnectionError("Proxy is not connected")

                self.connection = await asyncssh.connect(
                    host=self.ip,
                    username=self.user_name or os.environ.get("USER"),
                    password=self.user_pass,
                    client_factory=create_client_factory(self),
                    tunnel=tunnel,
                    connect_timeout=settings.DEFAULT_CONNECT_TIMEOUT,
                    keepalive_interval=settings.DEFAULT_KEEPALIVE,
                    known_hosts=None,
                )
            except (
                PermissionError,
                asyncssh.PermissionDenied,
            ) as exc:
                self.error = f"{exc.__class__.__name__}"
                self.state = initial_state
                self.logger.error(f"{self}: {self.state}: {self.error}: {exc}")
                semaphore.connection.release()
                raise
            except (
                socket.gaierror,
                TimeoutError,
                asyncio.exceptions.TimeoutError,
                ConnectionError,
                OSError,  # Network unreachable
                asyncssh.Error,
            ) as exc:
                self.error = f"{exc.__class__.__name__}"
                self.state = initial_state
                self.logger.error(f"{self}: {self.state}: {self.error}: {exc}")
                semaphore.connection.release()
                raise
            except Exception as exc:
                self.error = f"{exc.__class__.__name__}"
                self.state = initial_state
                self.logger.critical(f"{self}: {self.state}: {self.error}: {exc}")
                semaphore.connection.release()
                raise
            else:
                self.state = State.CONNECTED
                self.logger.info(f"{self}: {self.state}")

    async def disconnect(self) -> None:
        if self.connection is not None:
            self.connection.close()
            await self.connection.wait_closed()

    async def forward_local_port(self, port: int, host: str = "127.0.0.1") -> int:
        local_port = get_free_port()
        listener = await self.connection.forward_local_port(
            listen_host="127.0.0.1",
            listen_port=local_port,
            dest_host=host,
            dest_port=port,
        )
        self.forwarders[local_port] = listener
        return local_port

    async def forward_local_path(self, path: str) -> Path:
        local_path = get_temp_file()
        listener = await self.connection.forward_local_path(
            listen_path= local_path,
            dest_path=path,
        )
        self.forwarders[local_path] = listener
        return local_path

    async def close_forwarding(self, port_or_path):
        listener = self.forwarders.pop(port_or_path)
        listener.close()
        await listener.wait_closed()
        if isinstance(port_or_path, Path):
            port_or_path.parent.rmdir()

    async def run(
        self,
        cmd: str,
        stdin: str | None = None,
        timeout: int | None = None,
    ) -> CmdExec:
        timeout = timeout if timeout is not None else settings.DEFAULT_CMD_TIMEOUT

        assert self.connection is not None

        execution = CmdExec(cmd)
        self.executions.append(execution)

        async with self.execute_semaphore:
            try:
                chan, session = await self.connection.create_session(
                    create_session_factory(
                        self,
                        execution,
                        stdout_received_callback=lambda data: print(data.decode(), end="", flush=True),
                        stderr_received_callback=lambda data: print(data.decode(), end="", flush=True),
                    ),
                    cmd,
                    encoding=None,
                )
                print(cmd, end="", flush=True)
                self.logger.info(f"{self}: execute `{cmd}`")
                if stdin is not None:
                    chan.write(stdin.encode(settings.DEFAULT_ENCODING))
                    chan.write_eof()

                await asyncio.wait_for(chan.wait_closed(), timeout=timeout)

                # done = asyncio.Event()
                # async def execute() -> None:
                #     try:
                #         await asyncio.wait_for(chan.wait_closed(), timeout=timeout)
                #     except (TimeoutError, asyncio.TimeoutError):
                #         chan.abort()
                #         raise
                #     finally:
                #         done.set()
                #
                # async def wait() -> None:
                #     try:
                #         await done.wait()
                #     except asyncio.CancelledError:
                #         chan.abort()
                #         raise
                #
                # await asyncio.gather(
                #     execute(),
                #     wait(),
                #     # done.wait(),
                # )

            except (
                TimeoutError,
                asyncio.TimeoutError,
                asyncssh.Error,
            ) as err:
                self.logger.error(f"{self}: execute `{cmd}`: {err.__class__.__name__}: {err}")
                # raise SSHExecutionError("{err.__class__.__name__}: {err}")
                raise
            except asyncio.CancelledError as err:
                self.logger.error(f"{self}: execute `{cmd}`: {err.__class__.__name__}: {err}")
                raise
            else:
                self.logger.info(
                    f"{self}: execute `{cmd}`: DONE: "
                    f"got reply: {len(execution.stdout_bytes)} bytes / {len(execution.stderr_bytes)} bytes"
                )
                if execution.stdout:
                    self.logger.debug(f"{self}: execute `{cmd}`: stdout:\n{execution.stdout}")
                if execution.stderr:
                    self.logger.debug(f"{self}: execute `{cmd}`: stderr:\n{execution.stderr}")

                self.executions.remove(execution)
                return execution

    async def download(self):
        pass

    async def upload(self):
        pass

def create_client_factory(ssh: SSH) -> type[asyncssh.SSHClient]:
    class SSHClient(asyncssh.SSHClient):
        def connection_lost(self, err: Exception | None) -> None:
            ssh.connection = None
            if err is None:
                ssh.state = State.DISCONNECTED
                ssh.logger.info(f"{ssh}: {ssh.state}")
            else:
                ssh.error = f"{err.__class__.__name__}"
                ssh.state = State.DISCONNECTED
                ssh.logger.error(f"{ssh}: {ssh.state}: {ssh.error}: {err}")
            semaphore.connection.release()
    return SSHClient

def create_session_factory(
    ssh: SSH,
    execution: CmdExec,
    stdout_received_callback: Callable[[bytes], None] | None = None,
    stderr_received_callback: Callable[[bytes], None] | None = None,
) -> type[asyncssh.SSHClientSession[bytes]]:
    class SSHClientSession(asyncssh.SSHClientSession[bytes]):
        def __init__(self) -> None:
            self.start_time = self.time = time()

        def exit_status_received(self, status: int) -> None:
            execution.exit_code = status

        def data_received(self, data: bytes, datatype: asyncssh.DataType) -> None:
            if datatype == asyncssh.EXTENDED_DATA_STDERR:
                execution.stderr_bytes += data
                if stderr_received_callback is not None:
                    stderr_received_callback(data)
            else:
                execution.stdout_bytes += data
                if stdout_received_callback is not None:
                    stdout_received_callback(data)
            current_time = time()
            if current_time - self.time > settings.LONG_REQUEST_LOG_TIMEOUT:
                ssh.logger.info(
                    f"{ssh}: execute `{execution.cmd}`: RUNNING: received "
                    f"{len(execution.stdout_bytes) + len(execution.stderr_bytes):,} bytes"
                    f" in {current_time - self.start_time:.0f} sec"
                )

                self.time = current_time

    return SSHClientSession


def get_free_port(host="127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))     # 0 = let OS choose
        return s.getsockname()[1]

def get_temp_file() -> Path:
    return Path(tempfile.mkdtemp()) / "sock"
