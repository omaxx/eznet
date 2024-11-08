import pathlib

from setuptools import find_packages, setup

pwd = pathlib.Path(__file__).parent
requirements_file = pathlib.Path(pwd, "requirements.txt")
requirements = requirements_file.read_text().splitlines()


setup(
    name="eznet",
    version="0.3.0",
    packages=find_packages(),
    url="https://github.com/omaxx/eznet",
    license="MIT",
    author="maxx orlov",
    author_email="maxx.orlov@gmail.com",
    description="",
    entry_points={
        "console_scripts": [
            "eznet=eznet.cli:cli",
        ]
    },
    install_requires=requirements,
    extras_require={
        'jsonnet': ['jsonnet'],
    },
)
