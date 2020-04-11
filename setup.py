from setuptools import setup

setup(
    name="zendown",
    version="0.1.0",
    author="Mitchell Kember",
    description="Tool for writing structured documentation",
    license="MIT",
    packages=["zendown", "zendown.templates"],
    python_requires=">=3.7",
    install_requires=[
        "Jinja2>=2,<3" "PyYAML>=4.2b1",
        "mistletoe<2",
        "python-slugify>=4,<5",
        "watchdog<2",
    ],
    package_data={"zendown.templates": ["*.jinja", "*.css"],},
    entry_points={"console_scripts": ["zd = zendown.cli:main"]},
)
