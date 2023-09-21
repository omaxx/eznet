from __future__ import annotations

import asyncio
import logging
import os
import socket
from enum import Enum, auto
from pathlib import Path
from time import time
from types import TracebackType
from typing import ClassVar, Dict, List, Optional, Tuple, Type, Union

import asyncssh

DEFAULT_CONNECT_TIMEOUT = 30
DEFAULT_CMD_TIMEOUT = 90
DEFAULT_KEEPALIVE = 5
DEFAULT_ENCODING = "latin-1"

MAX_SIMULTANEOUS_CONNECTIONS = 64
MAX_SIMULTANEOUS_EXECUTIONS = 64
MAX_SIMULTANEOUS_DOWNLOADS = 4
MAX_SIMULTANEOUS_UPLOADS = 4


class ConnectError(Exception):
    pass


class AuthenticationError(Exception):
    pass


class State(Enum):
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    WAITING_CONNECT = auto()
    WAITING_RECONNECT = auto()

    def __repr__(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.name


class SSH:
    def __init__(
        self,
        ip: Optional[str],
        user_name: Optional[str] = None,
        user_pass: Optional[str] = None,
        device: Optional[str] = None,
    ) -> None:
        self.ip = ip
        self.user_name = user_name or os.environ["USER"]
        self.user_pass = user_pass
        self.device = device

        if device is None:
            self.logger = logging.getLogger("eznet.device")
        else:
            self.logger = logging.getLogger(f"eznet.device.{device}")

        self.connection: Optional[asyncssh.SSHClientConnection] = None
        self.state = State.DISCONNECTED
        self.error: Optional[str] = None

        self.requests: List[Request] = []

    def __str__(self) -> str:
        if self.device is not None:
            return f"{self.device} (ip={self.ip or ''}): ssh"
        else:
            return f"{self.ip or super().__str__()}: ssh"

    async def __aenter__(self) -> None:
        await self.connect()

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        self.disconnect()

    async def connect(self, attempts: int = 1, attempt_timeout: int = 15) -> None:
        if self.ip is None:
            self.logger.warning(f"{self}: ip is not set")
            raise ConnectError()

        async with Lock.get(self).connect:
            if self.connection is not None:
                return

            self.state = State.WAITING_CONNECT
            await Semaphore.get().connect.acquire()
            while attempts > 0:
                self.state = State.CONNECTING
                self.logger.info(
                    f"{self}: connecting to {self.ip} as {self.user_name}"
                )
                try:
                    self.connection = await asyncssh.connect(
                        host=self.ip,
                        username=self.user_name,
                        password=self.user_pass,
                        client_factory=create_client_factory(self),
                        connect_timeout=DEFAULT_CONNECT_TIMEOUT,
                        keepalive_interval=DEFAULT_KEEPALIVE,
                        known_hosts=None,
                    )
                except (
                    socket.gaierror,
                    TimeoutError,
                    asyncio.exceptions.TimeoutError,
                    ConnectionRefusedError,
                    ConnectionResetError,
                    OSError,  # Network unreachable
                    asyncssh.Error,
                ) as err:
                    self.state = State.DISCONNECTED
                    self.error = f"{err.__class__.__name__}"
                    self.logger.error(f"{self}: {err.__class__.__name__}: {err}")
                    # Semaphore.get().connect.release()
                    # raise ConnectError() from None
                except Exception as err:
                    self.state = State.DISCONNECTED
                    self.error = f"{err.__class__.__name__}"
                    self.logger.critical(f"{self}: {err.__class__.__name__}: {err}")
                    Semaphore.get().connect.release()
                    raise
                else:
                    self.state = State.CONNECTED
                    self.error = None
                    self.logger.info(f"{self}: CONNECTED")
                    return

                attempts -= 1
                if attempts > 0:
                    self.state = State.WAITING_RECONNECT
                    await asyncio.sleep(attempt_timeout)

            Semaphore.get().connect.release()
            # raise ConnectError() from None

    def disconnect(self) -> None:
        if self.connection is not None:
            self.connection.close()

    async def execute(
        self, cmd: str, timeout: int = DEFAULT_CMD_TIMEOUT
    ) -> Tuple[Optional[str], Optional[str]]:
        if self.connection is not None:
            request = CmdRequest(cmd)
            self.requests.append(request)

            try:
                chan, session = await self.connection.create_session(
                    create_session_factory(request), cmd, encoding=DEFAULT_ENCODING,
                )
                self.logger.info(f"{self}: execute `{cmd}`: waiting for reply")
                # TODO: add watchguard
                # await chan.wait_closed()
                await asyncio.wait_for(chan.wait_closed(), timeout=timeout)
            except (
                asyncio.TimeoutError,
                asyncssh.Error,
            ) as err:
                self.logger.error(
                    f"{self}: execute `{cmd}`: {err.__class__.__name__}: {err}"
                )
                self.error = f"{err.__class__.__name__}"
                # raise CommandError()
                return None, None
            else:
                self.logger.info(
                    f"{self}: execute `{cmd}`: "
                    f"got reply: {len(request.stdout)} bytes / {len(request.stderr)} bytes"
                )
                if request.stdout:
                    self.logger.debug(
                        f"{self}: execute `{cmd}`: stdout:\n{request.stdout}"
                    )
                if request.stderr:
                    self.logger.debug(
                        f"{self}: execute `{cmd}`: stderr:\n{request.stderr}"
                    )

                self.requests.remove(request)
                return request.stdout, request.stderr

        self.logger.warning(f"{self}: execute `{cmd}` no active connection")
        # raise CommandError()
        return None, None

    async def download(self, src: str, dst: Union[str, Path]) -> List[str]:
        download_files: List[str] = []

        async with Semaphore.get().download:
            request = FileRequest(src)
            t0 = t1 = time()
            r1 = 0

            def progress_handler(
                src_file: bytes, dst_file: bytes, received: int, total: int
            ) -> None:
                if dst_file.decode(DEFAULT_ENCODING) not in download_files:
                    download_files.append(dst_file.decode(DEFAULT_ENCODING))
                nonlocal t0, t1, r1, request

                if request.file_name != src_file.decode(DEFAULT_ENCODING):
                    self.requests.remove(request)
                    request = FileRequest(src_file.decode(DEFAULT_ENCODING))
                    self.requests.append(request)

                request.received_bytes = received
                request.total_bytes = total

                t_delta = time() - t1
                if received == total:
                    t_delta = time() - t0
                    received_part = received / total if total > 0 else 1
                    speed = received / t_delta
                    self.logger.info(
                        f"{self}: download `{src_file.decode('ascii')}`: {received:,} of {total:,}:"
                        f" {received_part:.0%} at {speed:,.0f} Bps"
                    )
                    t0 = t1 = time()
                    r1 = 0
                    request.speed = speed
                elif t_delta > 10:
                    received_part = received / total if total > 0 else 1
                    speed = (received - r1) / t_delta
                    self.logger.info(
                        f"{self}: downloading `{src_file.decode('ascii')}`: {received:,} of {total:,}:"
                        f" {received_part:.0%} at {speed:,.0f} Bps"
                    )
                    t1 = time()
                    r1 = received
                    request.speed = speed

            try:
                self.requests.append(request)
                await asyncssh.scp(
                    (self.connection, src),
                    dst,
                    progress_handler=progress_handler,
                    preserve=True,
                    recurse=True,
                )
            except (
                asyncssh.SFTPError,
                asyncssh.SFTPFailure,
            ) as err:
                self.logger.error(
                    f"{self}: download `{src}` --> `{dst}`: {err.__class__.__name__}: {err}"
                )
            else:
                self.logger.info(f"{self}: download `{src}` --> `{dst}`: DONE")
            finally:
                self.requests.remove(request)
                return download_files

    async def upload(self, src: Union[str, Path], dst: str) -> List[str]:
        upload_files: List[str] = []

        async with Semaphore.get().upload:
            request = FileRequest(src)
            t0 = t1 = time()
            r1 = 0

            def progress_handler(
                src_file: bytes, dst_file: bytes, received: int, total: int
            ) -> None:
                if dst_file.decode(DEFAULT_ENCODING) not in upload_files:
                    upload_files.append(dst_file.decode(DEFAULT_ENCODING))
                nonlocal t0, t1, r1, request

                if request.file_name != src_file.decode(DEFAULT_ENCODING):
                    self.requests.remove(request)
                    request = FileRequest(src_file.decode(DEFAULT_ENCODING))
                    self.requests.append(request)

                request.received_bytes = received
                request.total_bytes = total

                t_delta = time() - t1
                if received == total:
                    t_delta = time() - t0
                    received_part = received / total if total > 0 else 1
                    speed = received / t_delta
                    self.logger.info(
                        f"{self}: upload `{src_file.decode('ascii')}`: {received:,} of {total:,}:"
                        f" {received_part:.0%} at {speed:,.0f} Bps"
                    )
                    t0 = t1 = time()
                    r1 = 0
                    request.speed = speed
                elif t_delta > 10:
                    received_part = received / total if total > 0 else 1
                    speed = (received - r1) / t_delta
                    self.logger.info(
                        f"{self}: uploading `{src_file.decode('ascii')}`: {received:,} of {total:,}:"
                        f" {received_part:.0%} at {speed:,.0f} Bps"
                    )
                    t1 = time()
                    r1 = received
                    request.speed = speed

            try:
                self.requests.append(request)
                await asyncssh.scp(
                    src,
                    (self.connection, dst),
                    progress_handler=progress_handler,
                    preserve=True,
                    recurse=True,
                )
            except (
                asyncssh.SFTPError,
                asyncssh.SFTPFailure,
            ) as err:
                self.logger.error(
                    f"{self}: upload `{src}` --> `{dst}`: {err.__class__.__name__}: {err}"
                )
            else:
                self.logger.info(f"{self}: upload `{src}` --> `{dst}`: DONE")
            finally:
                self.requests.remove(request)
                return upload_files


def create_client_factory(ssh: SSH) -> Type[asyncssh.SSHClient]:
    class SSHClient(asyncssh.SSHClient):
        def connection_lost(self, err: Optional[Exception]) -> None:
            if ssh.connection is not None:
                ssh.connection = None
                ssh.state = State.DISCONNECTED
                Semaphore.get().connect.release()
                if err is None:
                    ssh.logger.info(f"{ssh}: DISCONNECTED")
                else:
                    ssh.logger.error(f"{ssh}: DISCONNECTED: {err}")
                    ssh.error = f"{err.__class__.__name__}"
                    # ssh.status = Status.ERROR

                    # try:
                    #     loop = asyncio.get_running_loop()
                    #     loop.create_task(ssh.connect(
                    #         attempts=RECONNECT_ATTEMPTS,
                    #         attempt_timeout=RECONNECT_ATTEMPT_TIMEOUT,
                    #     ))
                    # except RuntimeError as err:
                    #     ssh.logger.critical(f"{ssh}: reconnect error: {err}")

    return SSHClient


def create_session_factory(request: CmdRequest) -> Type[asyncssh.SSHClientSession[str]]:
    class SSHClientSession(asyncssh.SSHClientSession[str]):
        def data_received(self, data: str, datatype: asyncssh.DataType) -> None:
            if datatype == asyncssh.EXTENDED_DATA_STDERR:
                request.stderr += data
            else:
                request.stdout += data

    return SSHClientSession


class Request:
    pass


class CmdRequest(Request):
    def __init__(self, cmd: str):
        self.cmd = cmd
        self.stdout = ""
        self.stderr = ""

    def __repr__(self) -> str:
        return f"{self.cmd}\t{len(self.stdout):,}\t/\t{len(self.stderr):,}"


class FileRequest(Request):
    def __init__(self, file_name: str, received_bytes: int = 0, total_bytes: int = 0):
        self.file_name = file_name
        self.received_bytes = received_bytes
        self.total_bytes = total_bytes
        self.speed: float = 0

    def __repr__(self) -> str:
        received_part = (
            self.received_bytes / self.total_bytes if self.total_bytes > 0 else 1
        )
        return (
            f"{self.file_name}\t"
            f"{self.received_bytes:,}\tof\t{self.total_bytes:,}\t"
            f"[ {received_part:.0%} ]\t"
            f"at {self.speed:,.0f} Bps"
        )


class Lock:
    loop: ClassVar[Optional[asyncio.AbstractEventLoop]] = None
    instances: ClassVar[Dict[int, Lock]] = {}

    def __init__(self) -> None:
        self.connect = asyncio.Lock()

    @classmethod
    def get(cls, ssh: SSH) -> Lock:
        loop = asyncio.get_running_loop()
        if Lock.loop != loop:
            Lock.loop = loop
            Lock.instances = {}
        if id(ssh) not in Lock.instances:
            Lock.instances[id(ssh)] = Lock()
        return Lock.instances[id(ssh)]


class Semaphore:
    loop: ClassVar[Optional[asyncio.AbstractEventLoop]] = None
    instances: ClassVar[Optional[Semaphore]] = None

    def __init__(self) -> None:
        self.connect = asyncio.Semaphore(MAX_SIMULTANEOUS_CONNECTIONS)
        self.execute = asyncio.Semaphore(MAX_SIMULTANEOUS_EXECUTIONS)
        self.download = asyncio.Semaphore(MAX_SIMULTANEOUS_DOWNLOADS)
        self.upload = asyncio.Semaphore(MAX_SIMULTANEOUS_UPLOADS)

    @classmethod
    def get(cls) -> Semaphore:
        loop = asyncio.get_running_loop()
        if Semaphore.loop != loop or Semaphore.instances is None:
            Semaphore.loop = loop
            Semaphore.instances = Semaphore()
        return Semaphore.instances
