"""Tooling for building Zendown targets."""

import os
import os.path

# from zendown.files import get_target_file

targets = ["docx", "html", "latex"]

# generic path utility
# cat/sec/art#id
# layouts/...

# remember implicitly extend from config.
# also set vars for lang, target. can test {% if ...}

# facility for parsing the yaml headers, whitelisted so others equivalent to
# jinja2 {% set ... %}

# macros image.html.en.txt
# or just image.html.txt
# or image.ALL.txt

# what if building both langs ... manual with both. should path be
# {en,fr,BOTH}/{art1,art2,ALL} or {art1,art2,ALL}/{en,fr,BOTH}?
def build_target(target, article, language, args):
    build_dir = os.path.join("build", target, language)
    if not os.path.exists(build_dir):
        os.makedirs(build_dir)
