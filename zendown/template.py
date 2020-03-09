"""Zendown template file parser."""

import re

import yaml


class Template:
    def __init__(self):
        self.parent = None
        self.targets = []
        self.language = ""
        self.options = {}
        self.content = ""

    def render(self):
        pass
