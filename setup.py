from setuptools import setup, find_packages

setup(
    name="viral_script_engine",
    version="0.1.0",
    packages=find_packages(exclude=["viral_script_engine/venv*"]),
)
