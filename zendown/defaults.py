"""Default files for a Zendown project."""

from textwrap import dedent


def structure(name):
    """Default project structure."""
    return {
        name: {
            "assets": {"tiger.jpg": ""},
            "content": {"first.txt": first_article},
            "data": {"config.yml": f"project_name: {name}"},
            "templates": {"footer.txt": footer_template},
            "macros": {"image.txt": image_macro},
        }
    }


first_article = dedent(
    """\
    ---
    extends: layouts/footer
    title: My first article
    targets: html
    ---

    This is my first article in {{project_name}}!

    {{image tiger.jpg}}
"""
)


footer_template = dedent(
    """\
    ---

    [[body]]

    ***

    I'm a footer!
"""
)


image_macro = dedent(
    """\
    <img src="assets/{{arg1}}">
"""
)
