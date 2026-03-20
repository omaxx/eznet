from __future__ import annotations
from typing import Literal
from pathlib import Path
import random
import string

from .device import Device, device_method
from .run import cli_cmd


@device_method()
async def download(
    device: Device,
    remote_path: Path | str,
    local_path: Path | str = ".",
    re: Literal["re0", "re1", "both", ""] = "",
    host: bool = False,
    tmp_folder: str = "/tmp",
) -> None:
    if isinstance(remote_path, str):
        remote_path = Path(remote_path)
    if host:
        remote_path = "/hostvar" / remote_path.relative_to("/var")
    if isinstance(local_path, str):
        local_path = Path(local_path)
    if not local_path.exists():
        local_path.mkdir(parents=True)

    local_file_name = remote_path.name
    tmp_file_name = ''.join(random.choices(string.ascii_lowercase, k=4)) + "." + local_file_name

    if re in ["re0", "both"]:
        await device(cli_cmd(f"file copy re0:{remote_path} {tmp_folder}/re0.{tmp_file_name}", timeout=300))
        await device.ssh.download(f"{tmp_folder}/re0.{tmp_file_name}", f"{local_path}/re0.{local_file_name}")
        await device(cli_cmd(f"file delete {tmp_folder}/re0.{tmp_file_name}"))

    if re in ["re1", "both"]:
        await device(cli_cmd(f"file copy re1:{remote_path} {tmp_folder}/re1.{tmp_file_name}", timeout=300))
        await device.ssh.download(f"{tmp_folder}/re1.{tmp_file_name}", f"{local_path}/re1.{local_file_name}")
        await device(cli_cmd(f"file delete {tmp_folder}/re1.{tmp_file_name}"))

    if re == "":
        await device.ssh.download(f"{remote_path}", f"{local_path}/{local_file_name}")


@device_method()
async def download_tar(
    device: Device,
    remote_path: Path | str,
    local_path: Path | str = ".",
    re: Literal["re0", "re1", "both", ""] = "",
    tmp_folder: str = "/tmp",
) -> None:
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

    await device(cli_cmd(
        f'request routing-engine execute command '
        f'"tar -czf {tmp_folder}/{tmp_file_name} {remote_path}"'
        f'{re_command}',
        timeout=300,
    ))

    if re in ["re0", "both"]:
        await device(cli_cmd(f"file rename re0:{tmp_folder}/{tmp_file_name} {tmp_folder}/re0.{tmp_file_name}", timeout=300))
        await device.ssh.download(f"{tmp_folder}/re0.{tmp_file_name}", f"{local_path}/re0.{local_file_name}")
        await device(cli_cmd(f"file delete {tmp_folder}/re0.{tmp_file_name}"))

    if re in ["re1", "both"]:
        await device(cli_cmd(f"file rename re1:{tmp_folder}/{tmp_file_name} {tmp_folder}/re1.{tmp_file_name}", timeout=300))
        await device.ssh.download(f"{tmp_folder}/re1.{tmp_file_name}", f"{local_path}/re1.{local_file_name}")
        await device(cli_cmd(f"file delete {tmp_folder}/re1.{tmp_file_name}"))

    if re == "":
        await device.ssh.download(f"{tmp_folder}/{tmp_file_name}", f"{local_path}/{local_file_name}")
        await device(cli_cmd(f"file delete {tmp_folder}/{tmp_file_name}"))
