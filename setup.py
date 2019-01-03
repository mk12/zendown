from setuptools import setup

setup(
    name="zendown",
    version="0.1.0",
    author="Mitchell Kember",
    description="Tool for writing structured documentation",
    license="MIT",
    packages=["zendown"],
    install_requires=["jinja2>=2,<3"],
    entry_points={"console_scripts": ["zendown = zendown.cli:main"]},
)
