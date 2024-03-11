from __future__ import annotations

from typing import Optional, Type, Dict, Tuple, List, Union
from types import TracebackType

import asyncssh
import asyncio
import os
import logging
import socket
from collections import defaultdict
from time import time
from pathlib import Path

from .base import *

DEFAULT_CONNECT_TIMEOUT = 30
DEFAULT_CMD_TIMEOUT = 180
DEFAULT_KEEPALIVE = 5
DEFAULT_RECONNECT_TIMEOUT = 15
DEFAULT_ENCODING = "latin-1"

MAX_SIMULTANEOUS_CONNECTIONS = 64
MAX_SIMULTANEOUS_EXECUTIONS = 64
MAX_SIMULTANEOUS_DOWNLOADS = 2
MAX_SIMULTANEOUS_UPLOADS = 2

LONG_REQUEST_LOG_TIMEOUT = 10

MODULE = __name__.split(".")[0]

connection_semaphore: Dict[asyncio.AbstractEventLoop, asyncio.Semaphore] = defaultdict(
    lambda: asyncio.Semaphore(MAX_SIMULTANEOUS_CONNECTIONS)
)
execute_semaphore: Dict[asyncio.AbstractEventLoop, asyncio.Semaphore] = defaultdict(
    lambda: asyncio.Semaphore(MAX_SIMULTANEOUS_EXECUTIONS)
)
download_semaphore: Dict[asyncio.AbstractEventLoop, asyncio.Semaphore] = defaultdict(
    lambda: asyncio.Semaphore(MAX_SIMULTANEOUS_DOWNLOADS)
)
upload_semaphore: Dict[asyncio.AbstractEventLoop, asyncio.Semaphore] = defaultdict(
    lambda: asyncio.Semaphore(MAX_SIMULTANEOUS_UPLOADS)
)


class SSH:
    def __init__(
        self,
        ip: str,
        user_name: Optional[str] = None,
        user_pass: Optional[str] = None,
        root_pass: Optional[str] = None,
        device_id: Optional[str] = None,
    ):
        self.ip = ip
        self.user_name = user_name or os.environ["USER"]
        self.user_pass = user_pass
        self.root_pass = root_pass
        self.device_id = device_id

        if device_id is None:
            self.logger = logging.getLogger(f"{MODULE}.device")
        else:
            self.logger = logging.getLogger(f"{MODULE}.device.{device_id}")

        self.connection: Optional[asyncssh.SSHClientConnection] = None
        self.state = State.DISCONNECTED
        self.error: Optional[str] = None
        self.lock: Dict[asyncio.AbstractEventLoop, asyncio.Lock] = defaultdict(asyncio.Lock)

        self.requests: List[Request] = []

    def __str__(self) -> str:
        if self.device_id is not None:
            return f"{self.device_id} (ip={self.ip or ''}): ssh"
        else:
            return f"{self.ip}: ssh"

    async def __aenter__(self) -> None:
        await self.connect()

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        self.disconnect()

    async def connect(
        self,
        attempts: int = 1,
        connect_timeout: int = DEFAULT_CONNECT_TIMEOUT,
        reconnect_timeout: int = DEFAULT_RECONNECT_TIMEOUT,
    ) -> None:
        async with self.lock[asyncio.get_running_loop()]:
            if self.connection is not None:
                return
            self.state = State.WAITING_CONNECT
            self.error = None
            await connection_semaphore[asyncio.get_running_loop()].acquire()
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
                        connect_timeout=connect_timeout,
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
                except asyncio.exceptions.CancelledError as err:
                    self.state = State.DISCONNECTED
                    self.error = f"{err.__class__.__name__}"
                    self.logger.error(f"{self}: {err.__class__.__name__}: {err}")
                    connection_semaphore[asyncio.get_running_loop()].release()
                    raise
                except Exception as err:
                    self.state = State.DISCONNECTED
                    self.error = f"{err.__class__.__name__}"
                    self.logger.critical(f"{self}: {err.__class__.__name__}: {err}")
                    connection_semaphore[asyncio.get_running_loop()].release()
                    raise
                else:
                    self.state = State.CONNECTED
                    self.logger.info(f"{self}: CONNECTED")
                    return

                attempts -= 1
                if attempts > 0:
                    self.state = State.WAITING_RECONNECT
                    await asyncio.sleep(reconnect_timeout)

            connection_semaphore[asyncio.get_running_loop()].release()
            raise ConnectError(self.error)

    def disconnect(self) -> None:
        if self.connection is not None:
            self.connection.close()

    async def execute(
        self,
        cmd: str,
        password: Optional[str] = None,
        timeout: int = DEFAULT_CMD_TIMEOUT,
    ) -> Tuple[str, str]:
        if self.connection is None:
            self.logger.warning(f"{self}: execute `{cmd}` not connected")
            raise RequestError("Not connected")

        request = CmdRequest(cmd)
        self.requests.append(request)

        async with execute_semaphore[asyncio.get_running_loop()]:
            try:
                chan, session = await self.connection.create_session(
                    create_session_factory(self, request), cmd, encoding=None,
                )
                self.logger.info(f"{self}: execute `{cmd}`")
                if password is not None:
                    chan.write(password.encode(DEFAULT_ENCODING))
                    chan.write_eof()

                done = asyncio.Event()

                async def wait() -> None:
                    try:
                        await done.wait()
                    except asyncio.CancelledError:
                        chan.abort()
                        raise

                async def run_cmd() -> None:
                    try:
                        await asyncio.wait_for(chan.wait_closed(), timeout=timeout)
                    except (TimeoutError, asyncio.TimeoutError):
                        chan.abort()
                        raise
                    finally:
                        done.set()

                await asyncio.gather(
                    run_cmd(),
                    wait(),
                )

            except (
                TimeoutError,
                asyncio.TimeoutError,
                asyncssh.Error,
            ) as err:
                self.logger.error(
                    f"{self}: execute `{cmd}`: {err.__class__.__name__}: {err}"
                )
                self.error = f"{err.__class__.__name__}"
                raise RequestError(self.error)
            except asyncio.CancelledError as err:
                self.logger.error(
                    f"{self}: execute `{cmd}`: {err.__class__.__name__}: {err}"
                )
                raise
            else:
                self.logger.info(
                    f"{self}: execute `{cmd}`: DONE: "
                    f"got reply: {len(request.stdout_bytes)} bytes / {len(request.stderr_bytes)} bytes"
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

    async def download(self, src: str, dst: Union[str, Path]) -> List[str]:
        download_files: List[str] = []

        async with download_semaphore[asyncio.get_running_loop()]:
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
                elif t_delta > LONG_REQUEST_LOG_TIMEOUT:
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
                # workaround for avoiding async.scp stucks during cancel
                done = asyncio.Event()

                async def download() -> None:
                    try:
                        await asyncssh.scp(
                            (self.connection, src),
                            dst,
                            progress_handler=progress_handler,
                            preserve=True,
                            recurse=True,
                        )
                    finally:
                        done.set()
                await asyncio.gather(download(), done.wait())
            except (
                asyncssh.SFTPError,
                asyncssh.SFTPFailure,
            ) as err:
                self.logger.error(
                    f"{self}: download `{src}` --> `{dst}`: {err.__class__.__name__}: {err}"
                )
            except asyncio.CancelledError as err:
                self.logger.error(
                    f"{self}: download `{src}` --> `{dst}`: {err.__class__.__name__}: {err}"
                )
                raise
            else:
                self.logger.info(f"{self}: download `{src}` --> `{dst}`: DONE")
            finally:
                self.requests.remove(request)
                return download_files

    async def upload(self, src: Union[str, Path], dst: str) -> List[str]:
        upload_files: List[str] = []

        async with upload_semaphore[asyncio.get_running_loop()]:
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
                elif t_delta > LONG_REQUEST_LOG_TIMEOUT:
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
                # workaround for avoiding async.scp stucks during cancel
                done = asyncio.Event()

                async def upload() -> None:
                    try:
                        await asyncssh.scp(
                            src,
                            (self.connection, dst),
                            progress_handler=progress_handler,
                            preserve=True,
                            recurse=True,
                        )
                    finally:
                        done.set()
                await asyncio.gather(upload(), done.wait())
            except (
                asyncssh.SFTPError,
                asyncssh.SFTPFailure,
            ) as err:
                self.logger.error(
                    f"{self}: upload `{src}` --> `{dst}`: {err.__class__.__name__}: {err}"
                )
            except asyncio.CancelledError as err:
                self.logger.error(
                    f"{self}: download `{src}` --> `{dst}`: {err.__class__.__name__}: {err}"
                )
                raise
            else:
                self.logger.info(f"{self}: upload `{src}` --> `{dst}`: DONE")
            finally:
                self.requests.remove(request)
                return upload_files


class Request:
    pass


class CmdRequest(Request):
    def __init__(self, cmd: str):
        self.cmd = cmd
        self.stdout_bytes = bytearray()
        self.stderr_bytes = bytearray()

    @property
    def stdout(self) -> str:
        return self.stdout_bytes.decode(encoding=DEFAULT_ENCODING, errors="ignore")

    @property
    def stderr(self) -> str:
        return self.stderr_bytes.decode(encoding=DEFAULT_ENCODING, errors="ignore")

    def __repr__(self) -> str:
        return f"{self.cmd}\t{len(self.stdout_bytes):,}\t/\t{len(self.stderr_bytes):,}"


class FileRequest(Request):
    def __init__(self, file_name: Union[str, Path], received_bytes: int = 0, total_bytes: int = 0):
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


def create_client_factory(ssh: SSH) -> Type[asyncssh.SSHClient]:
    class SSHClient(asyncssh.SSHClient):
        def connection_lost(self, err: Optional[Exception]) -> None:
            if ssh.connection is not None:
                ssh.connection = None
                ssh.state = State.DISCONNECTED
                connection_semaphore[asyncio.get_running_loop()].release()
                if err is None:
                    ssh.logger.info(f"{ssh}: DISCONNECTED")
                else:
                    ssh.logger.error(f"{ssh}: DISCONNECTED: {err}")
                    ssh.error = f"{err.__class__.__name__}"

                    # try:
                    #     loop = asyncio.get_running_loop()
                    #     loop.create_task(ssh.connect(
                    #         attempts=RECONNECT_ATTEMPTS,
                    #         attempt_timeout=RECONNECT_ATTEMPT_TIMEOUT,
                    #     ))
                    # except RuntimeError as err:
                    #     ssh.logger.critical(f"{ssh}: reconnect error: {err}")

    return SSHClient


def create_session_factory(ssh: SSH, request: CmdRequest) -> Type[asyncssh.SSHClientSession[str]]:
    class SSHClientSession(asyncssh.SSHClientSession[str]):
        def __init__(self) -> None:
            self.start_time = self.time = time()
            # self.rcvd: int = 0

        def data_received(self, data: bytes, datatype: asyncssh.DataType) -> None:
            if datatype == asyncssh.EXTENDED_DATA_STDERR:
                request.stderr_bytes += data
            else:
                request.stdout_bytes += data
            current_time = time()
            if current_time - self.time > LONG_REQUEST_LOG_TIMEOUT:
                ssh.logger.info(
                    f"{ssh}: execute `{request.cmd}`: RUNNING: received "
                    f"{len(request.stdout_bytes) + len(request.stderr_bytes):,} bytes"
                    f" in {current_time - self.start_time:.0f} sec"
                )

                self.time = current_time
                # self.rcvd = len(request.stdout) + len(request.stderr)

    return SSHClientSession
