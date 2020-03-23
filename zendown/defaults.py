"""Default files for a Zendown project."""

from zendown import config


def structure(name):
    """Default project structure."""
    return {
        name: {
            ".gitignore": gitignore,
            "zendown.yml": f"project_name: {name}",
            "assets": {"tiger.jpg": ""},
            "articles": {"first.txt": first_article},
            "templates": {"page.txt": page_template},
            "macros": {"image.txt": image_macro},
            "targets": {"html.yml": "extends: builtin_html"},
        }
    }


gitignore = """\
# Zendown specific
/out/

# OS generated files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
Icon?
ehthumbs.db
Thumbs.db

# Editors
.vscode/

# Artifacts
*.pyo
*.pyc
__pycache__
"""


first_article = """\
extends: templates/page
title: My first article

---

This is my first article in {{config.project_name}}!

{{image tiger.jpg}}
"""


page_template = """\
---

[[body]]

***

I'm a footer!
"""


image_macro = """\
<img src="assets/{{arg1}}">
"""
