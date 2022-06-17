import logging
import socket
import threading
from typing import List, Tuple, Union

import paramiko
import scp
from tqdm import tqdm

SSH_AUTO_ADD = True

SSH_CONNECT_TIMEOUT = 30
SSH_CMD_TIMEOUT = 30
SSH_CMD_PING_TIMEOUT = 5
SSH_KEEPALIVE = 15


class DeviceError(Exception):
    pass


class DeviceConnectError(DeviceError):
    pass


class DeviceAuthError(DeviceError):
    pass


class DeviceCommandError(DeviceError):
    pass


class SSH:
    def __init__(self,
                 ip: str,
                 name: str = None,
                 port: int = None,
                 user_name: str = None,
                 user_password: str = None,
                 root_password: str = None,
                 logger: logging.Logger = None
                 ):
        self.name = name or ip
        self.ip = ip
        self.port = port or 22
        self.user_name = user_name
        self.user_password = user_password
        self.root_password = root_password
        self.logger = logger or logging.getLogger(__name__)

        self.ssh_connect_lock = threading.Lock()
        self.ssh = paramiko.SSHClient()
        if SSH_AUTO_ADD:
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def __str__(self):
        return self.name

    def __bool__(self):
        return self.ip is not None

    def is_connected(self, ping: bool = False) -> bool:
        if self.ssh.get_transport() and self.ssh.get_transport().is_active():
            if ping:
                try:
                    self.ssh_exec("", auto_connect=False, timeout=SSH_CMD_PING_TIMEOUT)
                except DeviceConnectError:
                    return False
            return True
        else:
            return False

    def connect(self) -> None:
        if self.ip is None:
            raise DeviceConnectError(f"{self}: ip is not set")
        with self.ssh_connect_lock:
            if self.is_connected():
                return
            try:
                self.logger.debug(f"{self}: ssh_connect: starting ssh to {self.ip}")
                self.ssh.connect(
                    hostname=self.ip,
                    username=self.user_name,
                    password=self.user_password,
                    timeout=SSH_CONNECT_TIMEOUT,
                )
                if SSH_KEEPALIVE is not None:
                    self.ssh.get_transport().set_keepalive(SSH_KEEPALIVE)
            except paramiko.AuthenticationException as err:
                self.logger.error(f"{self}: ssh_connect: AUTH_ERROR: {err} with username {self.user_name}")
                raise DeviceAuthError(err)
            except paramiko.SSHException as err:
                self.logger.error(f"{self}: ssh_connect: CONNECT_ERROR: {err}")
                raise DeviceConnectError(err)
            except (socket.timeout, TimeoutError):
                self.logger.error(f"{self}: ssh_connect: CONNECT_ERROR: timeout")
                raise DeviceConnectError("ssh timeout")
            except socket.gaierror:
                self.logger.error(f"{self}: ssh_connect: CONNECT_ERROR: ip for {self.ip} not found")
                raise DeviceConnectError(f"ip for {self.ip} not found")

            self.logger.info(f"{self}: ssh_connect: CONNECTED")

    def disconnect(self) -> None:
        self.ssh.close()
        self.logger.info(f"{self}: ssh_disconnect: DISCONNECTED")

    def ssh_exec(self,
                 cmd: str,
                 timeout: int = SSH_CMD_TIMEOUT,
                 auto_connect: bool = True,
                 ) -> Tuple[str, str]:
        if auto_connect:
            self.connect()
        try:
            self.logger.info(f"{self}: ssh_exec: {cmd}")
            _, stdout, stderr = self.ssh.exec_command(cmd, timeout=timeout)
            output = stdout.read().decode('ascii', 'replace')
            self.logger.debug(f"{self}: ssh_exec: {cmd} reply:\n{output}")
            error = stderr.read().decode('ascii', 'replace')
            return output, error
        except paramiko.SSHException as err:
            self.logger.error(f"{self}: ssh_exec: ERROR: {err}")
            self.disconnect()
            raise DeviceConnectError(err)
        except (socket.timeout, TimeoutError):
            self.logger.error(f"{self}: ssh_exec: ERROR: timeout")
            self.disconnect()
            raise DeviceConnectError("ssh timeout")

    def run_cmd(self, cmd, timeout=SSH_CMD_TIMEOUT):
        output, _ = self.ssh_exec(cmd, timeout)
        error = output[1:-1].split(": ", 1)
        if error[0] == "error":
            self.logger.error(f"{self}: run_cmd: ERROR: {error[1]}")
            raise DeviceCommandError(error[1])
        else:
            return output

    def scp_get(self,
                remote: str,
                local: str,
                progress: bool = True,
                ) -> List[str]:
        self.connect()
        self.logger.info(f"{self}: download {remote} to {local}")
        pb: Union[FileCopy, FileCopyPB]
        if progress:
            pb = FileCopyPB()
        else:
            pb = FileCopy()
        show_progress = pb.show_progress
        scp_client = scp.SCPClient(self.ssh.get_transport(), progress=show_progress, sanitize=lambda x: x)
        scp_client.get(remote, local, preserve_times=True, recursive=True)
        scp_client.close()
        return [file.decode("ascii") for file in pb.files]


SSH.get_file = SSH.scp_get


class FileCopyPB:
    def __init__(self):
        self.pb = tqdm(unit="bytes", ascii=True)
        self.files = []

    def __del__(self):
        self.pb.close()

    def show_progress(self, file, size, sent):
        if len(self.files) == 0:
            self.files.append(file)
            # FIXME
            self.pb.desc = file.decode("utf-8").rsplit("/", 1)[-1]
            # self.pb.desc = file.decode("utf-8")
            self.pb.total = size
        elif self.files[-1] != file:
            self.pb.close()
            self.pb = tqdm(unit="bytes", ascii=True)
            self.files.append(file)
            self.pb.desc = file.decode("utf-8").rsplit("/", 1)[-1]
            # self.pb.desc = file.decode("utf-8")
            self.pb.total = size
        self.pb.n = sent
        self.pb.display()


class FileCopy:
    def __init__(self):
        self.files = []

    def show_progress(self, file, *args):
        if len(self.files) == 0:
            self.files.append(file)
        elif self.files[-1] != file:
            self.files.append(file)
