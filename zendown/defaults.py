"""Default files for a Zendown project."""

from textwrap import dedent


first_article = dedent(
    """\
    extends: layouts/footer
    title: My first article
    targets: html

    ---

    This is my first article in {{project_name}}!

    {{image tiger.jpg}}
"""
)


footer_layout = dedent(
    """\
    ---

    {{body}}

    ***

    I'm a footer!
"""
)


image_macro = dedent(
    """\
    <img src="assets/{{args[1]}}">
"""
)


html_target = dedent(
    """\

"""
)


def config_file(project_name):
    return f"project_name: {project_name}\n"
