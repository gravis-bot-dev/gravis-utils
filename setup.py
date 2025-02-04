from setuptools import setup, find_packages

setup(
    name="gravis_utils",
    version="1.0.0",
    author="gravis8888",
    packages=find_packages(),
    install_requires=["discord.py"],
    include_package_data=True,
)