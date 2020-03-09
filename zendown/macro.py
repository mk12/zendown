"""Zendown macro file parser."""

import re

import yaml


class Macro:
    def __init__(self):
        self.target = ""
        self.language = ""
        self.options = {}
        self.content = ""

    def render(self):
        pass
