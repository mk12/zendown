"""Command-line interface."""

import argparse
from pathlib import Path
import sys

from zendown.build import BuildError, Options, builders
from zendown.files import create_project
from zendown.project import Project


def main():
    parser, commands = get_parser()
    args = parser.parse_args()
    if args.command == "help":
        if args.help_target:
            commands[args.help_target].print_help()
        else:
            parser.print_help()
    else:
        command = globals()[f"command_{args.command}"]
        assert command, "unexpected command name"
        command(args)


def get_parser():
    parser = argparse.ArgumentParser(
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

    parser_build = commands.add_parser("build", help="build the project")
    parser_build.add_argument(
        "-i",
        "--ignore-errors",
        action="store_true",
        help="keep going if there are errors",
    )
    parser_build.add_argument("builder", choices=builders.keys(), help="build target")
    parser_build.add_argument(
        "query", nargs="?", default="", help="filter articles by ref",
    )

    return parser, commands.choices


def command_new(args):
    print(f"Creating a new Zendown project in {args.name}/")
    create_project(Path.cwd(), args.name)


def command_list(args):
    project = Project.find()
    for article in project.query(args.query):
        print(article.path if args.files else article.node.ref)


def command_build(args):
    project = Project.find()
    builder = builders[args.builder](project)
    articles = project.query(args.query)
    options = Options(ignore_errors=args.ignore_errors)
    try:
        builder.build(articles, options)
    except BuildError as ex:
        # ANSI escape code for red, bold text.
        print(f"\x1b[31;1mERROR:\x1b[0m {ex}")
        sys.exit(1)
