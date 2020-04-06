"""Command-line interface."""

import logging
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Any, Mapping, Tuple

from zendown.build import Options, builders
from zendown.files import create_project
from zendown.logs import setup_logging
from zendown.project import Project
from zendown.tokens import collect_text


def main():
    parser, commands = get_parser()
    args = parser.parse_args()
    if args.command == "help":
        if args.help_target:
            commands[args.help_target].print_help()
        else:
            parser.print_help()
        return

    log_level = logging.WARNING
    if args.verbose and args.verbose == 1:
        log_level = logging.INFO
    elif args.verbose and args.verbose >= 2:
        log_level = logging.DEBUG
    exit_level = logging.ERROR
    if args.keep_going:
        exit_level = logging.FATAL
    setup_logging(sys.stderr, log_level, exit_level)

    command = globals()[f"command_{args.command}"]
    assert command, "unexpected command name"
    command(args)


def get_parser() -> Tuple[ArgumentParser, Mapping[str, ArgumentParser]]:
    parser = ArgumentParser(
        prog="zendown", description="tool for building Zendown projects"
    )
    commands = parser.add_subparsers(metavar="command", dest="command", required=True)

    parser_help = commands.add_parser("help", help="show this help message and exit")
    parser_help.add_argument(
        metavar="command",
        dest="help_target",
        nargs="?",
        help="get help for a specific command",
    )

    parser_new = commands.add_parser("new", help="create a new project")
    parser_new.add_argument("name", help="project name")

    parser_list = commands.add_parser("list", help="list project items")
    parser_list.add_argument(
        "-f", "--files", action="store_true", help="show file paths instead of refs"
    )
    parser_list.add_argument(
        "query", nargs="?", default="", help="filter articles by ref",
    )

    parser_info = commands.add_parser("info", help="show article information")
    parser_info.add_argument(
        "-o", "--outline", action="store_true", help="show article outline"
    )
    parser_info.add_argument(
        "-l", "--links", action="store_true", help="show incoming/outgoing links"
    )
    parser_info.add_argument(
        "-a", "--assets", action="store_true", help="show assets referenced"
    )
    parser_info.add_argument(
        "-i", "--includes", action="store_true", help="show includes referenced"
    )
    parser_info.add_argument(
        "query", nargs="?", default="", help="filter articles by ref",
    )

    parser_build = commands.add_parser("build", help="build the project")
    parser_build.add_argument("builder", choices=builders.keys(), help="build target")
    parser_build.add_argument(
        "query", nargs="?", default="", help="filter articles by ref",
    )

    for subparser in [parser_new, parser_list, parser_info, parser_build]:
        subparser.add_argument(
            "-k",
            "--keep-going",
            action="store_true",
            help="keep going if there are errors",
        )
        subparser.add_argument(
            "-v",
            "--verbose",
            action="count",
            help="increase loggging (can use multiple times)",
        )

    return parser, commands.choices


def command_new(args: Namespace):
    print(f"Creating a new Zendown project in {args.name}/")
    create_project(Path.cwd(), args.name)


def command_list(args: Namespace):
    project = Project.find()
    for article in project.query(args.query):
        print(article.path if args.files else article.node.ref)


def command_build(args: Namespace):
    project = Project.find()
    builder = builders[args.builder](project, Options())
    articles = project.query(args.query)
    builder.build(articles)


def command_info(args: Namespace):
    project = Project.find()
    printer = InfoPrinter()
    for article in project.query(args.query):
        article.ensure_resolved(project)
        assert article.cfg
        printer.topic(article.node.ref)
        printer.heading("Title")
        printer.item(article.cfg["title"])
        if args.outline:
            printer.heading("Outline")
            for section in article.sections:
                leader = "#" * section.heading.level
                text = collect_text(section.heading)
                printer.item(f"{leader} {text}")
        if args.links:
            printer.heading("Outgoing links")
            for link in article.links:
                printer.item(link)
            printer.heading("Incoming links")
            for source in project.inverse_links[article]:
                printer.item(source.node.ref)
        if args.assets:
            printer.heading("Assets")
            for asset in article.assets:
                printer.item(asset.node.ref)
        if args.includes:
            printer.heading("Includes")
            for include in article.includes:
                printer.item(include.node.ref)


class InfoPrinter:

    """Helper class for implementing command_info."""

    def __init__(self):
        self.first = True

    def topic(self, s: Any):
        if not self.first:
            print()
        self.first = False
        print(s)

    def heading(self, s: Any):
        print(f"\n    {s}:")

    def item(self, s: Any):
        print(f"    {s}")
