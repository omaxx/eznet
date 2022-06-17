from setuptools import setup, find_packages
import pathlib

pwd = pathlib.Path(__file__).parent
requirements_file = pathlib.Path(pwd, "requirements.txt")
install_requires = requirements_file.read_text().splitlines()


setup(
    name='eznet',
    version='0.3.0',
    packages=find_packages(),
    url='https://github.com/omaxx/eznet',
    license='',
    author='maxx orlov',
    author_email='',
    description='',
    # entry_points={
    #     'console_scripts': 'eznet=eznet.cli:cli',
    # },
    install_requires=install_requires,
)
