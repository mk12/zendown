from setuptools import setup

setup(
    name="zendown",
    version="0.1.0",
    author="Mitchell Kember",
    description="Tool for writing structured documentation",
    license="MIT",
    packages=["zendown"],
    install_requires=["Jinja2>=2,<3", "PyYAML>=3,<4", "pypandoc>=1,<2"],
    entry_points={"console_scripts": ["zendown = zendown.cli:main"]},
)
