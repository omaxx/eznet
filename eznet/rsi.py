from __future__ import annotations

from pathlib import Path
from typing import Union, Iterable, List

from eznet import Device


def cli_commands(device: Device) -> Iterable[str]:
    commands: List[str] = [
        "show system information",
        "show version",
        "show version invoke-on all-routing-engines",
        "show system uptime",
        "show system uptime invoke-on all-routing-engines",
        "show system alarms",
        "show system process",
        "show system memory",
        "show system core-dumps",
        "show system core-dumps routing-engine both",
        "show system core-dumps all-members",
        "show system core-dumps satellite",
        "show krt queue",
        "show chassis alarms",
        "show chassis alarms satellite",
        "show chassis hardware",
        "show chassis hardware models",
        "show chassis firmware",
        "show chassis routing-engine",
        "show chassis fpc",
        "show chassis fpc pic-status",
        *([
            f"show chassis pic fpc-slot {fpc_number} pic-slot {pic_number}"
            for fpc_number, fpc in device.info.chassis.fpc().items()
            for pic_number in fpc.pics.keys()

        ] if device.info.chassis.fpc else []),
        "show chassis satellite",
        "show chassis satellite detail",
        "show chassis satellite software",
        "show chassis satellite extended-port",
        "show interfaces summary",
        "show interfaces",
        "show lacp interfaces",
        "show lldp detail",
        "show lldp neighbors",
        "show route summary",
        "show route forwarding-table summary",
        "show route cumulative vpn-family inet.0",
        "show route cumulative vpn-family inet6.0",
        "show bgp summary",
        "show bfd session",
    ]
    yield from commands


def pfe_commands(device: Device) -> Iterable[str]:
    commands: List[str] = [
        "show heap",
        "show syslog messages",
    ]
    yield from commands


def shell_commands(device: Device) -> Iterable[str]:
    commands: List[str] = [
        "ls -l",
        "ls -l /var/db/scripts/op",
        "ls -l /var/db/scripts/event",
        "ls -l /var/db/scripts/commit",
    ]
    yield from commands


def host_commands(device: Device) -> Iterable[str]:
    commands: List[str] = [
        *([
            "date +'%Y-%m-%d %H:%M:%S'",
            "ps -elf",
            "free -m",
          ] if device.info.system.info and device.info.system.info().sw_family in ["junos-qfx"] else []),
    ]
    # commands: List[str] = []
    yield from commands


def arch_re_commands(device: Device) -> Iterable[str]:
    commands: List[str] = [
        "file archive compress source /var/log destination /var/tmp/var.log.tgz",
        "file archive source /config/juniper.conf.*.gz destination /var/tmp/config.tar",
        "file archive source /var/db/config/juniper.conf.*.gz destination /var/tmp/var.db.config.tar",
    ]
    yield from commands


def arch_re_files(device: Device) -> Iterable[str]:
    files: List[str] = [
        "/var/tmp/var.log.tgz",
        "/var/tmp/config.tar",
        "/var/tmp/var.db.config.tar",
    ]
    yield from files


def arch_host_commands(device: Device) -> Iterable[str]:
    commands: List[str] = [
        "tar cvfz /var/tmp/hostvar.log.tgz /var/log",
        "mkdir -p /var/tmp/dcpfe",
        "scp -o StrictHostKeyChecking=no 192.168.1.16:/var/log/*.log /var/tmp/dcpfe",
        "tar cvfz /var/tmp/dcpfe.log.tgz /var/tmp/dcpfe",
        "rm -rf /var/tmp/dcpfe",
    ]
    yield from commands


def arch_host_files(device: Device) -> Iterable[str]:
    files: List[str] = [
        "/hostvar/tmp/hostvar.log.tgz",
        "/hostvar/tmp/dcpfe.log.tgz",
    ]
    yield from files


def log_files(device: Device) -> Iterable[str]:
    files: List[str] = [
        "/var/log/messages*",
        "/var/log/chassis*",
        "/var/log/authorization-commands*",
    ]
    yield from files


async def process(
    device: Device,
    job_path: Union[Path, str],
) -> None:
    if isinstance(job_path, str):
        job_path = Path(job_path)

    with open(job_path / f"{device.id}.info", "w") as io:
        print(await device.info.system.info.fetch(), file=io)
        print(await device.info.chassis.re.fetch(), file=io)
        print(await device.info.chassis.fpc.fetch(), file=io)
        print(await device.info.system.uptime.fetch(), file=io)

    if not job_path.exists():
        job_path.mkdir(parents=True)

    with open(job_path / f"{device.id}.cmd", "w") as io:
        for cmd in cli_commands(device):
            print(f"{' ' + cmd + ' ':=^120}", file=io)
            output = await device.junos.run_cmd(cmd)
            if output is not None:
                print(output, file=io)
            print(f"{' ' + cmd + ' ':^^120}", file=io)
            print(file=io)

        for cmd in shell_commands(device):
            print(f"{' ' + cmd + ' ':=^120}", file=io)
            output = await device.junos.run_shell_cmd(cmd)
            if output is not None:
                print(output, file=io)
            print(f"{' ' + cmd + ' ':^^120}", file=io)
            print(file=io)

    for fpc_number in device.info.chassis.fpc().keys():
        with open(job_path / f"{device.id}.fpc{fpc_number}", "w") as io:
            for cmd in pfe_commands(device):
                print(f"{' ' + cmd + ' ':=^120}", file=io)
                output = await device.junos.run_pfe_cmd(cmd, fpc=fpc_number)
                if output is not None:
                    print(output, file=io)
                print(f"{' ' + cmd + ' ':^^120}", file=io)
                print(file=io)

    # for file in log_files(device):
    #     remote_path = Path(file)
    #     if remote_path.is_absolute():
    #         local_path = job_path / f"{device.id}" / remote_path.parent.relative_to("/")
    #     else:
    #         local_path = job_path / f"{device.id}" / remote_path.parent
    #     if not local_path.exists():
    #         local_path.mkdir(parents=True)
    #     await device.ssh.download(file, local_path)
    #

    device_job_path = job_path / f"{device.id}"
    if not device_job_path.exists():
        device_job_path.mkdir(parents=True)
    await device.junos.download("/var/log", device_job_path)

    # with open(job_path / f"{device.id}.rsi", "w") as io:
    #     output = await device.junos.run_cmd("request support information", timeout=600)
    #     if output is not None:
    #         print(output, file=io)
