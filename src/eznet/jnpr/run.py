from __future__ import annotations
from typing import Literal

from .device import Device, device_method


DEFAULT_CMD_TIMEOUT = 180


class CommandError(Exception):
    pass


def _check_output_for_errors(
    device: Device,
    cmd: str,
    output: str,
) -> None:
    # Junos cli return error in 2nd line of stdout as `error: syntax error, expecting <command>: ...`
    try:
        output_error = output.split("\n")[1].split(": ", 1)
        if output_error[0] == "error":
            if device is not None and cmd is not None:
                device.logger.warning(f"{device}: run_cli `{cmd}`: ERROR: {output_error[1]}")
            raise CommandError(f"{output_error[1]}")
    except IndexError:
        pass


@device_method(prefix="run")
async def cli_cmd(
    device: Device,
    cmd: str,
    timeout: int = DEFAULT_CMD_TIMEOUT,
) -> str:
    result = await device.ssh.run(cmd, timeout=timeout)
    _check_output_for_errors(device, cmd, result.stdout)
    return result.stdout


@device_method(prefix="run")
async def shell_cmd(
    device: Device,
    cmd: str,
    timeout: int = DEFAULT_CMD_TIMEOUT,
    as_root: bool = False,
    re: Literal["re0", "re1"] | None = None,
) -> str:
    if not as_root:
        result = await device.ssh.run(
            f'start shell command "{cmd}"',
            timeout=timeout,
        )
        output = result.stdout
    else:
        if device.root_pass is None:
            raise CommandError()
        if re is None:
            result = await device.ssh.run(
                f'start shell user root command "{cmd}"',
                # stdin=self.device.root_pass,
                timeout=timeout,
            )
        else:
            result = await device.ssh.run(
                f"start shell user root command \"rsh -Ji {re} '{cmd}'\"",
                # stdin=self.device.root_pass,
                timeout=timeout,
            )
        output = result.stdout[9:]
    _check_output_for_errors(device, cmd, output)
    if result.stderr is not None and result.stderr != "":
        device.logger.warning(f"{device}: run_shell_cmd: ERROR: {result.stderr.strip()}")
        raise CommandError(f"{result.stderr.strip()}")
    return output


@device_method(prefix="run")
async def pfe_cmd(
    device: Device,
    cmd: str,
    fpc: int = 0,
    timeout: int = DEFAULT_CMD_TIMEOUT,
) -> str:
    result = await device.ssh.execute(
        f'request pfe execute target fpc{fpc} command "{cmd}" timeout 0',
        timeout=timeout,
    )
    _check_output_for_errors(device, cmd, result.stdout)
    try:
        command, error, output = result.stdout.split("\n", 2)
        if "error" in error:
            device.logger.warning(f"{device}: run_pfe_cmd: ERROR: {error}")
            raise CommandError(f"{error}")
    except ValueError:
        raise CommandError()
    return output


@device_method(prefix="run")
async def re_cmd(
    device: Device,
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
    result = await device.ssh.run(
        f'request routing-engine execute {cmd_re} command "{cmd}"',
        timeout=timeout,
    )
    _check_output_for_errors(device, cmd, result.stdout)
    return result.stdout
