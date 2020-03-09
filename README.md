# Zendown

Zendown is a system for writing documentation, built for technical writers.

- **Simple structure**: Articles are files. Sections are directories.
- **Separation of content and presentation**: When you're writing, focus on the content. When you're styling, focus on presentation.
- **Extensible Markdown**: Write yours docs in [Pandoc Markdown][pandoc], and extend it with custom macros.
- **Advanced templating**: Avoid repetition by creating [Jinja][jinja2] templates for different kinds of articles.
- **Multiple languages**: Write your docs in as many languages as you want.
- **Multiple targets**: Deploy to HTML, PDF, or a custom format.

[pandoc]: https://pandoc.org/MANUAL.html#pandocs-markdown
[jinja2]: http://jinja.pocoo.org

## Quick start

Clone the repository and run `make install`. You'll need Python 3 for this to work.

TODO: Basic quickstart using zendown.

## Contributing

For development, run `make dev`. This will download all dependencies and install Zendown in editable mode.

Run `make help` to see other targets, such as formatting and testing.

## License

© 2020 Mitchell Kember

Zendown is available under the MIT License; see LICENSE for details.
