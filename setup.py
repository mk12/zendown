from setuptools import setup

setup(
    name="zendown",
    version="0.1.0",
    author="Mitchell Kember",
    description="Tool for writing structured documentation",
    license="MIT",
    packages=["zendown"],
    install_requires=["PyYAML>=3,<4", "mistletoe<2"],
    entry_points={"console_scripts": ["zd = zendown.cli:main"]},
)
