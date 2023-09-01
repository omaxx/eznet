from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional, Tuple

from lxml import etree
from lxml.etree import _Element  # noqa

from .ssh import SSH

# from .common import CommandError

DEFAULT_CMD_TIMEOUT = 90


class JUNOS:
    def __init__(
        self,
        ssh: SSH,
    ):
        self.ssh = ssh
        self.logger = ssh.logger

    def __str__(self) -> str:
        return f"{self.ssh}: junos"

    def output_has_errors(
        self,
        cmd: str,
        output: str,
    ) -> bool:
        # Junos cli return error in 2nd line of stdout as `error: syntax error, expecting <command>: ...`
        try:
            output_error = output.split("\n")[1].split(": ", 1)
            if output_error[0] == "error":
                self.logger.error(f"{self}: run_cmd `{cmd}`: ERROR: {output_error[1]}")
                # raise CommandError()
                return True
        except IndexError:
            pass

        return False

    async def run_cmd(
        self,
        cmd: str,
        timeout: int = DEFAULT_CMD_TIMEOUT,
    ) -> Optional[str]:
        output, _ = await self.ssh.execute(cmd, timeout=timeout)
        if output is None or self.output_has_errors(cmd, output):
            return None

        return output

    async def run_shell_cmd(
        self,
        cmd: str,
        timeout: int = DEFAULT_CMD_TIMEOUT,
    ) -> Optional[str]:
        output, error = await self.ssh.execute(
            f'start shell command "{cmd}"', timeout=timeout
        )
        # First check for junos error in stdout
        if output is None or self.output_has_errors(cmd, output):
            return None

        # Second check for error in stderr
        if error is not None and error != "":
            self.logger.error(f"{self}: run_shell_cmd: ERROR: {error.strip()}")
            return output

        return output

    async def run_pfe_cmd(
        self,
        cmd: str,
        fpc: int = 0,
        timeout: int = DEFAULT_CMD_TIMEOUT,
    ) -> Optional[str]:
        output, _ = await self.ssh.execute(
            f'request pfe execute target fpc{fpc} command "{cmd}"', timeout=timeout
        )

        # First check for junos error in stdout
        if output is None or self.output_has_errors(cmd, output):
            return None

        # Second check if pfe return error in stdout 2nd line as `Syntax error at 'wrong'`
        try:
            command, error, output = output.split("\n", 2)
            if "error" in error:
                self.logger.error(f"{self}: run_pfe_cmd: ERROR: {error}")
                return None
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
        # First check for junos error in stdout
        if output is None or self.output_has_errors(cmd, output):
            return None

        # TODO:
        # There is no option to detect error in host shell output :(

        return output

    async def run_xml_cmd(
        self,
        cmd: str,
        timeout: int = DEFAULT_CMD_TIMEOUT,
    ) -> Optional[_Element]:
        output, _ = await self.ssh.execute(f"{cmd} | display xml", timeout=timeout)

        # First check for junos error in stdout
        if output is None or self.output_has_errors(cmd, output):
            return None

        output = output.replace(" xmlns=", " xmlnamespace=").replace("junos:", "")
        try:
            xml = etree.fromstring(output)
        except etree.XMLSyntaxError:
            self.logger.error(f"{self}: run_xml_cmd: xml parse error")
            return None

        # TODO:
        # Verify xml for errors
        # if :
        #     self.logger.error(f"{self}: junos: run_xml_cmd: xml parse error")
        #     return None

        return xml

    async def run_json_cmd(
        self,
        cmd: str,
        timeout: int = DEFAULT_CMD_TIMEOUT,
    ) -> Optional[Dict[Any, Any]]:
        output, _ = await self.ssh.execute(f"{cmd} | display json", timeout=timeout)

        # First check for junos error in stdout
        if output is None or self.output_has_errors(cmd, output):
            return None

        json_output = json.loads(output)
        if not isinstance(json_output, dict):
            self.logger.error(f"{self}: run_json_cmd: json parse error")
            return None

        return json_output

    async def config(
        self,
        config: str,
    ) -> bool:
        if self.ssh.connection is None:
            return False
        self.logger.debug(f"{self}: starting shell")
        stdin, stdout, stderr = await self.ssh.connection.open_session(
            # request_pty=True,
            # term_type='xterm-color',
            # term_size=(80, 24),
        )
        stdin.write("\n")
        while True:
            line = await stdout.readline()
            prompt_match = re.match(r"\w+@[\w.-]+>", line)
            if prompt_match:
                prompt = prompt_match.group(0)[:-1]
                break

        self.logger.debug(f"{self}: ssh shell: got prompt `{prompt}`")

        async def send(cmd: Optional[str] = None) -> Tuple[str, str]:
            if cmd is not None:
                self.logger.debug(f"{self}: ssh shell: sending `{cmd}`")
                stdin.write(cmd + "\n")
            _reply = (await stdout.readuntil(prompt))[0: -len(prompt)]
            self.logger.debug(f"{self}: ssh shell: receive:\n{_reply}")
            _mode = (await stdout.readexactly(2))[0]
            self.logger.debug(f"{self}: ssh shell: mode: `{_mode}`")
            return _reply, _mode

        await send()
        reply, mode = await send("configure private")
        if mode == "#":
            self.logger.info(f"{self}: ssh shell: enter config mode")
            for line in config.split("\n"):
                await send(line)

            reply, mode = await send("commit and-quit")
            if mode == ">":
                self.logger.info(f"{self}: ssh shell: commit successfull")
                return True
            elif mode == "#":
                self.logger.error(
                    f"{self}: ssh shell: commit failed, going to rollback"
                )
                await send("rollback")
                await send("exit")
        else:
            self.logger.error(f"{self}: ssh shell: could not enter to config mode")
        return False
