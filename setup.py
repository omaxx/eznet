import pathlib

from setuptools import find_packages, setup

pwd = pathlib.Path(__file__).parent
requirements_file = pathlib.Path(pwd, "requirements.txt")
install_requires = requirements_file.read_text().splitlines()


setup(
    name="eznet",
    version="0.1.4",
    packages=find_packages(),
    url="https://github.com/omaxx/eznet",
    license="",
    author="maxx orlov",
    author_email="",
    description="",
    entry_points={
        "console_scripts": [
            "eznet=eznet.__main__:run",
            "eznet_to_rundeck=eznet.scripts.export:main",
        ]
    },
    install_requires=install_requires,
)
