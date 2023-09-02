import logging
from pathlib import Path
from typing import Union

import asyncssh

SFTP_HOST = 'sftp.juniper.net'
SFTP_USER = "jtac"
SFTP_PASS = "anonymous"


logger = logging.getLogger(__name__)


async def upload(path: Union[str, Path], case: str) -> None:
    if isinstance(path, str):
        path = Path(path)
    async with asyncssh.connect(SFTP_HOST, username=SFTP_USER, password=SFTP_PASS) as conn:
        logger.info("sftp: connected")
        async with conn.start_sftp_client() as sftp:
            if not await sftp.exists(f"/pub/incoming/{case}"):
                await sftp.mkdir(f"/pub/incoming/{case}")
            if not path.is_dir():
                logger.info(f"sftp: {path} --> {path.name}")
                await sftp.put(path, f"/pub/incoming/{case}")
                logger.info("sftp: done")
            else:
                for file in path.glob("**/*"):
                    if not file.is_dir():
                        remote_name = str(file.relative_to(path)).replace('/', '.')
                        logger.info(f"sftp: {file} --> {remote_name}")
                        await sftp.put(file, f"/pub/incoming/{case}/{remote_name}")
                        logger.info("sftp: done")
