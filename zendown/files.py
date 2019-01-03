"""File structure for Zendown projects."""

import os.path

from zendown.utils import fatal_error


ARTICLE_TXT = """
---
layout: footer
title: My first article
targets: html
---

This is my first article in {{project_name}}!

{{image tiger.jpg}}
""".strip()


FOOTER_TXT = """
{{body}}

I'm a footer!
""".strip()


IMAGE_TXT = """
<img src="assets/{{args[1]}}">
""".strip()


HTML_TXT = """

""".strip()


def create_project(root, project_name):
    """Create the default project files and directories in root."""
    structure = {
        project_name: {
            "assets": {"tiger.jpg": ""},
            "content": {"article.txt": ARTICLE_TXT},
            "data": {"config.txt": f"project_name: {project_name}\n"},
            "layouts": {"footer.txt": FOOTER_TXT},
            "macros": {"image.txt": IMAGE_TXT},
            "targets": {"html.txt": HTML_TXT},
        }
    }

    def create(root, structure):
        for key, val in structure.items():
            path = os.path.join(root, key)
            if isinstance(val, dict):
                os.mkdir(path)
                create(path, val)
            else:
                assert isinstance(val, str)
                with open(path, "w") as f:
                    f.write(val)

    create(root, structure)


def _get_dir(*items):
    path = os.path.join(*items)
    if not os.path.exists(path):
        fatal_error(
            f"directory '{path}' not found (are you in a Zendown project?)"
        )
    if not os.path.isdir(path):
        fatal_error(f"'{path}' is not a directory")
    return path


def _get_file(*items):
    path = os.path.join(*items)
    if not os.path.exists(path):
        fatal_error(f"file '{path}' not found (are you in a Zendown project?)")
    if not os.path.isfile(path):
        fatal_error(f"'{path}' is not a file")
    return path


def is_text(path):
    return path.endswith(".txt")


def get_target_file(name):
    return _get_file("targets", f"{name}.txt")


def get_target_files():
    files = [f for f in os.listdir(_get_dir("targets")) if is_text(f)]
    files.sort()
    return files


def get_target_names():
    files = get_target_files()
    return [os.path.splitext(os.path.basename(f))[0] for f in files]
