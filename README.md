# Zendown

Zendown is a system for writing documentation, built for technical writers. Here are its main features:

- **Simple structure**: Articles are files. Sections are directories.
- **Separation of content and presentation**: When you're writing, focus on the content. When you're styling, focus on presentation.
- **Extensible Markdown**: Write yours docs in [Pandoc Markdown][pandoc], and extend it with custom macros.
- **Advanced templating**: Avoid repetition by creating [Jinja][jinja2] templates for different kinds of articles.
- **Multiple languages**: Write your docs in as many languages as you want.
- **Multiple targets**: Deploy to HTML, PDF, or a custom format.

[pandoc]: https://pandoc.org/MANUAL.html#pandocs-markdown
[jinja2]: http://jinja.pocoo.org

## Install

Clone the repository and run `pip3 install .` to install Zendown on your system.

## Usage

Zendown has three main commands:

- `zendown new NAME`: Create a new Zendown project with the given name.
- `zendown list THING`: List articles, languages, build targets, and more.
- `zendown build TARGET`: Build the given target for the current project.

Run `zendown -h` for more details.

## Development

For development, run `pip3 install -r requirements.txt`. This will download the dependencies and install Zendown in editable mode.

Use `precommit.sh` to format code and run tests.

## Dependencies

Zendown is written in Python 3.7. It uses the following packages:

- [jinja2](https://pypi.org/project/jinja2/)
- [pypandoc](https://pypi.org/project/pypandoc/)

## License

© 2020 Mitchell Kember

Zendown is available under the MIT License; see LICENSE for details.
