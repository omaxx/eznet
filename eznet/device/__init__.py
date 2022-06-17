from .data import Data
from .drivers import SSH
from .info import Info


class Device:
    def __init__(self,
                 name: str,
                 ip: str,
                 user_name: str,
                 user_password: str,
                 **kwargs
                 ):
        self.ssh = SSH(
            name=name,
            ip=ip,
            user_name=user_name,
            user_password=user_password,
        )
        self.data = Data.load(**kwargs)
        self.info = None

    def get_info(self):
        self.info = Info.load(self.ssh, self.data)

