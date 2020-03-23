"""Command-line interface for Zendown."""

import argparse
from pathlib import Path

from zendown.files import create_project
from zendown.project import Project, Kind
from zendown.utils import fatal_error


def main():
    """Entry point of the program."""
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
    """Create the command-line argument parser."""
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

    parser_init = commands.add_parser("init", help="create a new project")
    parser_init.add_argument("name", help="project name")

    parser_list = commands.add_parser("list", help="list project items")
    list_args = parser_list.add_mutually_exclusive_group()
    for short, long in [
        ("a", "articles"),
        ("e", "templates"),
        ("t", "targets"),
        ("m", "macros"),
        ("s", "assets"),
    ]:
        list_args.add_argument(
            f"-{short}", f"--{long}", action="store_true", help=f"list {long}"
        )
    list_args.add_argument(
        "query", metavar="arg", nargs="?", default="", help="query to filter listing"
    )

    parser_build = commands.add_parser("build", help="build the project")
    parser_build.add_argument("target", help="target to build")
    parser_build.add_argument("-a", "--article", help="article query")
    parser_build.add_argument(
        "target_args", metavar="arg", nargs="*", help="target-specific arguments"
    )

    return parser, commands.choices


def command_init(args):
    print(f"Creating a new Zendown project in {args.name}/")
    create_project(Path.cwd(), args.name)


def command_list(args):
    proj = Project.find()
    if args.articles:
        kind = Kind.ARTICLE
    elif args.templates:
        kind = Kind.TEMPLATE
    elif args.targets:
        kind = Kind.TARGET
    elif args.macros:
        kind = Kind.MACRO
    elif args.assets:
        kind = Kind.ASSET
    else:
        fatal_error("must specify something to list")
    nodes = proj.query(kind, args.query)
    print("\n".join(str(n.ref) for n in nodes))


def command_build(args):
    print(f"Building target {args.target}")
