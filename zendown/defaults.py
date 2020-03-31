"""Default files for a Zendown project."""

from base64 import b64decode

from zendown import macros


def structure(name):
    """Default project structure."""
    with open(macros.__file__) as f:
        macros_py = f.read()
    return {
        name: {
            ".gitignore": gitignore,
            "macros.py": macros_py,
            "zendown.yml": zendown_yml(name),
            "content": {"first.md": first_md},
            "assets": {"tiger.jpg": b64decode(tiger_jpg_base64)},
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


zendown_yml = """\
project_name: {0}
inline_code_macro: upper
smart_typography: true
""".format


first_md = """\
title: My first article

---

@toc

# Introduction

Here's a [self-link](/first).

![Photo of a tiger](tiger.jpg)

@note:
> Did you know tigers can weigh as much as 660 pounds?

# Conclusion

@upper{Macros} are `fun`!
"""


tiger_jpg_base64 = """\
/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBUODAsLDBkSEw8VHhsgHx4bHR0h
JTApISMtJB0dKjkqLTEzNjY2ICg7Pzo0PjA1NjP/2wBDAQkJCQwLDBgODhgzIh0iMzMzMzMzMzMzMzMz
MzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzP/wgARCAAWADwDAREAAhEBAxEB/8QA
GQAAAgMBAAAAAAAAAAAAAAAAAwQBAgYF/8QAGAEAAwEBAAAAAAAAAAAAAAAAAQIDAAT/2gAMAwEAAhAD
EAAAAM3w9B1woKo20F78USaxrnSCkINOjsunQ2GE6eE06SrI9A6qvDKRTU5dkRKCO//EACwQAAIBAwQB
AgMJAAAAAAAAAAECAwARIQQFEjEiFUEyUWETFkJSU3GBkfH/2gAIAQEAAT8Ag1AjQDo9dXoaxlUEZA7x
U+4iTDX4/P3p9UsaE8zex8eVbttkGhIASdXK8l/IGtkcvcdWrT6vg7eZPvYdU0izpx4q2fhHdMkStZos
00bsAVBGMW96HONFJBxnFaLaTr3bmroCfwqCT1fuvupA7qZEkACkygtyDdWsLYFiK1yNq9AC8sgZF4cb
EEXsCcjNhfFarSvDr9TCitGqSsF5Yul/E/XFv5vUEjwOqgKUPdjkVJqCHNnwah3WSZh2qoA1vnQ3aMwo
bMzk2PiALW/c16vPZXR3Q8r4+v8AlTbpN+rKPE9G1Pu+pKcWkZgwuLnqp93leKSEO/Aj4WsR/VNrPspS
DBGzLi+a9Q4eIhSv/8QAHxEAAwEAAQQDAAAAAAAAAAAAAAECEQMEEiFREyJB/9oACAECAQE/AGs1m6hz
5EmRDptYTGj4/J2i0wulJfNWfVYdBzU322/waUPBs1+h8aEkKFpk+j449CjFiFCOxH//xAAhEQACAgEE
AgMAAAAAAAAAAAAAAQIREgMEIVEQMRMiQf/aAAgBAwEBPwCi2kZWeicYRWXYhWWUUaW3epy+CG1gn9nZ
vNFVcBEePCn4eo/Zn+nyT7M7dszXRmz/2Q==
"""
