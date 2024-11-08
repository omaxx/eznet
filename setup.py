from pathlib import Path

import importlib.util
import sys
from setuptools import find_packages, setup


def import_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

version = import_from_path("version", Path(__file__).parent / "eznet" / "version.py")
requirements = (Path(__file__).parent / "requirements.txt").read_text().splitlines()

setup(
    name="eznet",
    version=version.__version__,
    packages=find_packages(),
    url=version.__url__,
    license="MIT",
    author=version.__author__,
    author_email=version.__author_email__,
    description="",
    entry_points={
        "console_scripts": [
            "eznet=eznet.cli:cli",
        ]
    },
    install_requires=requirements,
    extras_require={
        "jsonnet": ["jsonnet"],
    },
)
