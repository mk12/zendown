"""Tooling for building Zendown targets."""

import os
import os.path


def build_target(target_file):
    if not os.path.exists("build"):
        os.mkdir("build")
