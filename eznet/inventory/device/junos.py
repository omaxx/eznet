from __future__ import annotations

import json
import logging
import random
import string
from pathlib import Path
from typing import Any, Literal, Optional, Union
from xml.etree import ElementTree

from lxml import etree
from lxml.etree import _Element as Element  # noqa

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
                self.logger.warning(
                    f"{self}: run_cmd `{cmd}`: ERROR: {output_error[1]}"
                )
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

    async def run_re_cmd(
        self,
        cmd: str,
        re: Literal["re0", "re1", "local", "other", "master", "backup", "both"],
        cli: bool = False,
        timeout: int = DEFAULT_CMD_TIMEOUT,
    ) -> str:
        if re in ["re0", "re1"]:
            cmd_re: str = re
        elif re in ["local", "other", "master", "backup", "both"]:
            cmd_re = f"routing-engine {re}"
        else:
            raise TypeError()
        if cli:
            cmd = f"cli -c '{cmd}'"
        output, _ = await self.ssh.execute(
            f'request routing-engine execute {cmd_re} command "{cmd}"',
            timeout=timeout,
        )
        self.check_output_for_errors(cmd, output)
        return output

    async def run_shell_cmd(
        self,
        cmd: str,
        timeout: int = DEFAULT_CMD_TIMEOUT,
        as_root: bool = False,
        re: Optional[Literal["re0", "re1"]] = None,
    ) -> str:
        if not as_root:
            output, error = await self.ssh.execute(
                f'start shell command "{cmd}"',
                timeout=timeout,
            )
        else:
            if self.root_pass is None:
                raise CommandError()
            if re is None:
                output, error = await self.ssh.execute(
                    f'start shell user root command "{cmd}"',
                    password=self.root_pass,
                    timeout=timeout,
                )
            else:
                output, error = await self.ssh.execute(
                    f"start shell user root command \"rsh -Ji {re} '{cmd}'\"",
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

        return xml

    async def run_lxml_cmd(
        self,
        cmd: str,
        timeout: int = DEFAULT_CMD_TIMEOUT,
    ) -> Element:
        output, _ = await self.ssh.execute(f"{cmd} | display xml", timeout=timeout)

        # First check for junos error in stdout
        self.check_output_for_errors(cmd, output)

        output = output.replace(" xmlns=", " xmlnamespace=").replace("junos:", "")
        try:
            xml = etree.fromstring(output)
        except etree.XMLSyntaxError:
            self.logger.warning(f"{self}: run_xml_cmd: xml parse error")
            raise CommandError("xml parse error")

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
            ";".join(
                [
                    "configure private",
                    *config.split("\n"),
                    "commit and-quit",
                ]
            ),
            timeout=timeout,
        )

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
        tmp_file_name = (
            "".join(random.choices(string.ascii_lowercase, k=4)) + "." + local_file_name
        )
        if re in ["re0", "both"]:
            await self.run_cmd(
                f"file copy re0:{remote_path} {tmp_folder}/re0.{tmp_file_name}",
                timeout=300,
            )
            await self.ssh.download(
                f"{tmp_folder}/re0.{tmp_file_name}",
                f"{local_path}/re0.{local_file_name}",
            )
            await self.run_cmd(f"file delete {tmp_folder}/re0.{tmp_file_name}")

        if re in ["re1", "both"]:
            await self.run_cmd(
                f"file copy re1:{remote_path} {tmp_folder}/re1.{tmp_file_name}",
                timeout=300,
            )
            await self.ssh.download(
                f"{tmp_folder}/re1.{tmp_file_name}",
                f"{local_path}/re1.{local_file_name}",
            )
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
                f"{remote_path.relative_to('/')}".replace("/", ".").replace("*", "")
                + ".tgz"
            )
        else:
            local_file_name = (
                f"{remote_path}".replace("/", ".").replace("*", "") + ".tgz"
            )
        tmp_file_name = (
            "".join(random.choices(string.ascii_lowercase, k=4)) + "." + local_file_name
        )
        re_command = {
            "re0": " re0",
            "re1": " re1",
            "both": " routing-engine both",
            "": "",
        }[re]
        await self.run_cmd(
            f"request routing-engine execute command "
            f'"tar -czf {tmp_folder}/{tmp_file_name} {remote_path}"'
            f"{re_command}",
            timeout=300,
        )
        if re in ["re0", "both"]:
            await self.run_cmd(
                f"file rename re0:{tmp_folder}/{tmp_file_name} {tmp_folder}/re0.{tmp_file_name}",
                timeout=300,
            )
            await self.ssh.download(
                f"{tmp_folder}/re0.{tmp_file_name}",
                f"{local_path}/re0.{local_file_name}",
            )
            await self.run_cmd(f"file delete {tmp_folder}/re0.{tmp_file_name}")

        if re in ["re1", "both"]:
            await self.run_cmd(
                f"file rename re1:{tmp_folder}/{tmp_file_name} {tmp_folder}/re1.{tmp_file_name}",
                timeout=300,
            )
            await self.ssh.download(
                f"{tmp_folder}/re1.{tmp_file_name}",
                f"{local_path}/re1.{local_file_name}",
            )
            await self.run_cmd(f"file delete {tmp_folder}/re1.{tmp_file_name}")

        if re == "":
            await self.ssh.download(
                f"{tmp_folder}/{tmp_file_name}", f"{local_path}/{local_file_name}"
            )
            await self.run_cmd(f"file delete {tmp_folder}/{tmp_file_name}")

        return True
