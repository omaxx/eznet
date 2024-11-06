from __future__ import annotations

from typing import Optional, Literal, Any, Union
import json
import re as regexp
import logging
from pathlib import Path
import string
import random
from xml.etree import ElementTree

# from lxml import etree
# from lxml.etree import _Element as Element  # noqa

from .drivers.ssh import DEFAULT_CMD_TIMEOUT, SSH


class CommandError(Exception):
    pass


class Junos:
    logger: logging.Logger
    root_pass: Optional[str]

    @property
    def ssh(self) -> SSH:
        raise NotImplementedError()

    def check_output_for_errors(
        self,
        cmd: str,
        output: str,
    ) -> None:
        # Junos cli return error in 2nd line of stdout as `error: syntax error, expecting <command>: ...`
        try:
            output_error = output.split("\n")[1].split(": ", 1)
            if output_error[0] == "error":
                self.logger.warning(f"{self}: run_cmd `{cmd}`: ERROR: {output_error[1]}")
                raise CommandError(f"{output_error[1]}")
        except IndexError:
            pass

    async def run_cmd(
        self,
        cmd: str,
        timeout: int = DEFAULT_CMD_TIMEOUT,
    ) -> str:
        output, _ = await self.ssh.execute(cmd, timeout=timeout)
        self.check_output_for_errors(cmd, output)
        return output

    async def run_shell_cmd(
        self,
        cmd: str,
        timeout: int = DEFAULT_CMD_TIMEOUT,
        as_root: bool = False,
        re: Optional[Literal["re0", "re1"]] = None,
    ) -> Optional[str]:
        if not as_root:
            output, error = await self.ssh.execute(
                f'start shell command "{cmd}"',
                timeout=timeout,
            )
        else:
            if self.root_pass is None:
                return None
            if re is None:
                output, error = await self.ssh.execute(
                    f'start shell user root command "{cmd}"',
                    password=self.root_pass,
                    timeout=timeout,
                )
            else:
                output, error = await self.ssh.execute(
                    f'start shell user root command "rsh -Ji {re} \'{cmd}\'"',
                    password=self.root_pass,
                    timeout=timeout,
                )
            output = output[9:]
        self.check_output_for_errors(cmd, output)
        if error is not None and error != "":
            self.logger.warning(f"{self}: run_shell_cmd: ERROR: {error.strip()}")
            raise CommandError(f"{error.strip()}")
        return output

    async def run_pfe_cmd(
        self,
        cmd: str,
        fpc: int = 0,
        timeout: int = DEFAULT_CMD_TIMEOUT,
    ) -> Optional[str]:
        output, error = await self.ssh.execute(
            f'request pfe execute target fpc{fpc} command "{cmd}" timeout 0',
            timeout=timeout,
        )
        self.check_output_for_errors(cmd, output)
        try:
            command, error, output = output.split("\n", 2)
            if "error" in error:
                self.logger.warning(f"{self}: run_pfe_cmd: ERROR: {error}")
                raise CommandError(f"{error}")
        except ValueError:
            pass

        return output

    async def run_host_cmd(
        self,
        cmd: str,
        timeout: int = DEFAULT_CMD_TIMEOUT,
    ) -> Optional[str]:
        output, _ = await self.ssh.execute(
            f'request app-engine host-cmd "{cmd}"', timeout=timeout
        )
        self.check_output_for_errors(cmd, output)
        return output

    async def run_xml_cmd(
        self,
        cmd: str,
        timeout: int = DEFAULT_CMD_TIMEOUT,
    ) -> ElementTree.Element:
        output, _ = await self.ssh.execute(f"{cmd} | display xml", timeout=timeout)

        # First check for junos error in stdout
        self.check_output_for_errors(cmd, output)

        output = output.replace(" xmlns=", " xmlnamespace=").replace("junos:", "")
        try:
            xml = ElementTree.fromstring(output)
        # except etree.XMLSyntaxError:
        except ElementTree.ParseError:
            self.logger.warning(f"{self}: run_xml_cmd: xml parse error")
            raise CommandError("xml parse error")

        # TODO:
        # Check xml for errors
        # if :
        #     self.logger.warning(f"{self}: junos: run_xml_cmd: xml parse error")
        #     raise CommandError()
        return xml

    async def run_json_cmd(
        self,
        cmd: str,
        timeout: int = DEFAULT_CMD_TIMEOUT,
    ) -> dict[Any, Any]:
        output, _ = await self.ssh.execute(f"{cmd} | display json", timeout=timeout)

        # First check for junos error in stdout
        self.check_output_for_errors(cmd, output)

        json_output = json.loads(output)
        if not isinstance(json_output, dict):
            self.logger.warning(f"{self}: run_json_cmd: json parse error")
            raise CommandError("json parse error")

        return json_output

    async def config(
        self,
        config: str,
        timeout: int = DEFAULT_CMD_TIMEOUT,
    ) -> None:
        output, _ = await self.ssh.execute(
            ";".join([
                "configure private",
                *config.split('\n'),
                "commit and-quit",
            ]), 
            timeout=timeout,
        )

    # async def config(
    #     self,
    #     config: str,
    # ) -> bool:
    #     # if self.ssh is None or self.ssh.connection is None:
    #     #     return False
    #     self.logger.debug(f"{self}: starting shell")
    #     stdin, stdout, stderr = await self.ssh.connection.open_session(
    #         # request_pty=True,
    #         # term_type='xterm-color',
    #         # term_size=(80, 24),
    #     )
    #     stdin.write("\n")
    #     while True:
    #         line = await stdout.readline()
    #         prompt_match = regexp.match(r"\w+@[\w.-]+>", line)
    #         if prompt_match:
    #             prompt = prompt_match.group(0)[:-1]
    #             break

    #     self.logger.debug(f"{self}: ssh shell: got prompt `{prompt}`")

    #     async def send(cmd: Optional[str] = None) -> tuple[str, str]:
    #         if cmd is not None:
    #             self.logger.debug(f"{self}: ssh shell: sending `{cmd}`")
    #             stdin.write(cmd + "\n")
    #         _reply = (await stdout.readuntil(prompt))[0: -len(prompt)]
    #         self.logger.debug(f"{self}: ssh shell: receive:\n{_reply}")
    #         _mode = (await stdout.readexactly(2))[0]
    #         self.logger.debug(f"{self}: ssh shell: mode: `{_mode}`")
    #         return _reply, _mode

    #     await send()
    #     reply, mode = await send("configure private")
    #     if mode == "#":
    #         self.logger.info(f"{self}: ssh shell: enter config mode")
    #         for line in config.split("\n"):
    #             await send(line)

    #         reply, mode = await send("commit and-quit")
    #         if mode == ">":
    #             self.logger.info(f"{self}: ssh shell: commit successfull")
    #             return True
    #         elif mode == "#":
    #             self.logger.warning(
    #                 f"{self}: ssh shell: commit failed, going to rollback"
    #             )
    #             await send("rollback")
    #             await send("exit")
    #     else:
    #         self.logger.warning(f"{self}: ssh shell: could not enter to config mode")
    #     return False

    async def download(
        self,
        remote_path: Union[Path, str],
        local_path: Union[Path, str] = ".",
        re: Literal["re0", "re1", "both", ""] = "",
        host: bool = False,
        tmp_folder: str = "/tmp",
    ) -> bool:
        if self.ssh is None or self.ssh.connection is None:
            return False
        if isinstance(remote_path, str):
            remote_path = Path(remote_path)
        if host:
            try:
                remote_path = "/hostvar" / remote_path.relative_to("/var")
            except ValueError:
                return False
        if isinstance(local_path, str):
            local_path = Path(local_path)
        if not local_path.exists():
            local_path.mkdir(parents=True)
        local_file_name = remote_path.name
        tmp_file_name = ''.join(random.choices(string.ascii_lowercase, k=4)) + "." + local_file_name
        if re in ["re0", "both"]:
            await self.run_cmd(f"file copy re0:{remote_path} {tmp_folder}/re0.{tmp_file_name}", timeout=300)
            await self.ssh.download(f"{tmp_folder}/re0.{tmp_file_name}", f"{local_path}/re0.{local_file_name}")
            await self.run_cmd(f"file delete {tmp_folder}/re0.{tmp_file_name}")

        if re in ["re1", "both"]:
            await self.run_cmd(f"file copy re1:{remote_path} {tmp_folder}/re1.{tmp_file_name}", timeout=300)
            await self.ssh.download(f"{tmp_folder}/re1.{tmp_file_name}", f"{local_path}/re1.{local_file_name}")
            await self.run_cmd(f"file delete {tmp_folder}/re1.{tmp_file_name}")

        if re == "":
            await self.ssh.download(f"{remote_path}", f"{local_path}/{local_file_name}")

        return True

    async def download_tar(
        self,
        remote_path: Union[Path, str],
        local_path: Union[Path, str] = ".",
        re: Literal["re0", "re1", "both", ""] = "",
        tmp_folder: str = "/tmp",
    ) -> bool:
        if self.ssh is None or self.ssh.connection is None:
            return False
        if isinstance(remote_path, str):
            remote_path = Path(remote_path)
        if isinstance(local_path, str):
            local_path = Path(local_path)
        if not local_path.exists():
            local_path.mkdir(parents=True)
        if remote_path.is_absolute():
            local_file_name = (
                f"{remote_path.relative_to('/')}"
                .replace("/", ".")
                .replace("*", "")
                + ".tgz"
            )
        else:
            local_file_name = (
                f"{remote_path}"
                .replace("/", ".")
                .replace("*", "")
                + ".tgz"
            )
        tmp_file_name = ''.join(random.choices(string.ascii_lowercase, k=4)) + "." + local_file_name
        re_command = {
            "re0": " re0",
            "re1": " re1",
            "both": " routing-engine both",
            "": "",
        }[re]
        await self.run_cmd(
            f'request routing-engine execute command '
            f'"tar -czf {tmp_folder}/{tmp_file_name} {remote_path}"'
            f'{re_command}',
            timeout=300,
        )
        if re in ["re0", "both"]:
            await self.run_cmd(
                f"file rename re0:{tmp_folder}/{tmp_file_name} {tmp_folder}/re0.{tmp_file_name}",
                timeout=300,
            )
            await self.ssh.download(f"{tmp_folder}/re0.{tmp_file_name}", f"{local_path}/re0.{local_file_name}")
            await self.run_cmd(f"file delete {tmp_folder}/re0.{tmp_file_name}")

        if re in ["re1", "both"]:
            await self.run_cmd(
                f"file rename re1:{tmp_folder}/{tmp_file_name} {tmp_folder}/re1.{tmp_file_name}",
                timeout=300,
            )
            await self.ssh.download(f"{tmp_folder}/re1.{tmp_file_name}", f"{local_path}/re1.{local_file_name}")
            await self.run_cmd(f"file delete {tmp_folder}/re1.{tmp_file_name}")

        if re == "":
            await self.ssh.download(f"{tmp_folder}/{tmp_file_name}", f"{local_path}/{local_file_name}")
            await self.run_cmd(f"file delete {tmp_folder}/{tmp_file_name}")

        return True
