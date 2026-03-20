# from __future__ import annotations
# import re
#
# from .device import Device, device_method
# from .run import CommandError
#
#
# @device_method()
# async def config(
#     device: Device,
#     config_text: str,
# ) -> None:
#     device.logger.debug(f"{device}: starting shell")
#     stdin, stdout, stderr = await device.ssh.connection.open_session()
#     stdin.write("\n")
#     while True:
#         line = await stdout.readline()
#         prompt_match = re.match(r"\w+@[\w.-]+>", line)
#         if prompt_match:
#             prompt = prompt_match.group(0)[:-1]
#             break
#
#     device.logger.debug(f"{device}: ssh shell: got prompt `{prompt}`")
#
#     async def send(cmd: str | None = None) -> tuple[str, str]:
#         if cmd is not None:
#             device.logger.debug(f"{device}: ssh shell: sending `{cmd}`")
#             stdin.write(cmd + "\n")
#         _reply = (await stdout.readuntil(prompt))[0: -len(prompt)]
#         device.logger.debug(f"{device}: ssh shell: receive:\n{_reply}")
#         _mode = (await stdout.readexactly(2))[0]
#         device.logger.debug(f"{device}: ssh shell: mode: `{_mode}`")
#         return _reply, _mode
#
#     await send()
#     reply, mode = await send("configure private")
#     if mode == "#":
#         device.logger.info(f"{device}: ssh shell: enter config mode")
#         for line in config_text.split("\n"):
#             await send(line)
#
#         reply, mode = await send("commit and-quit")
#         if mode == ">":
#             device.logger.info(f"{device}: ssh shell: commit successfull")
#             return
#         elif mode == "#":
#             device.logger.warning(f"{device}: ssh shell: commit failed, going to rollback")
#             await send("rollback")
#             await send("exit")
#             raise CommandError("commit failed")
#     else:
#         device.logger.warning(f"{device}: ssh shell: could not enter to config mode")
#         raise CommandError("could not enter config mode")
