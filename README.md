# Zendown

Zendown is a tool for writing structured documentation.

## Install

You can run Zendown without installing it with `python3 zendown ...`. You must in the repository directory for this to work.

To install it on your system, run `pip3 install .`. This should make the `zendown` program available in your PATH.

## Usage

Zendown has three main commands:

- `zendown new NAME`: Create a new Zendown project with the given name.
- `zendown list`: List the build targets available for the current project.
- `zendown build TARGET`: Build the given target for the current project.

Run `zendown -h` for more details.

## Development

For development, run `pip3 install -r requirements.txt`. This will install Zendown in editable mode as well as its build and test dependencies.

Use `precommit.sh` to reformat code and run the tests.

## Dependencies

Zendown is written in Python 3.7. It uses the following packages:

- [jinja2](https://pypi.org/project/jinja2/)
- [pypandoc](https://pypi.org/project/pypandoc/)

## License

© 2018 Mitchell Kember

Zendown is available under the MIT License; see LICENSE for details.
