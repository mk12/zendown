"""Command-line interface for Zendown."""

import argparse

from zendown.files import create_project
from zendown.build import build_target


def command_new(args):
    print(f"Creating a new Zendown project in {args.name}/")
    create_project(".", args.name)


def command_list(args):
    if args.articles:
        print("TODO list articles")
    elif args.templates:
        print("TODO list templates")
    elif args.languages:
        print("TODO list languages")
    elif args.targets:
        print("TODO list targets")
    elif args.macros:
        print("TODO list macros")


def command_build(args):
    print(f"Building target {args.target}")
    build_target(
        args.target,
        article=args.article,
        language=args.language,
        args=args.target_args,
    )


def get_parser():
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="zendown", description="tool for building Zendown projects"
    )
    commands = parser.add_subparsers(
        metavar="command", dest="command", required=True
    )

    parser_help = commands.add_parser(
        "help", help="show this help message and exit"
    )
    parser_help.add_argument(
        metavar="command",
        dest="help_target",
        nargs="?",
        help="get help for a specific command",
    )

    parser_new = commands.add_parser("new", help="create a new project")
    parser_new.add_argument("name", help="project name")

    parser_list = commands.add_parser("list", help="list project items")
    list_args = parser_list.add_mutually_exclusive_group()
    for short, long in [
        ("a", "articles"),
        ("e", "templates"),
        ("l", "languages"),
        ("t", "targets"),
        ("m", "macros"),
    ]:
        list_args.add_argument(
            f"-{short}", f"--{long}", action="store_true", help=f"list {long}"
        )

    parser_build = commands.add_parser("build", help="build the project")
    parser_build.add_argument("target", help="target to build")
    parser_build.add_argument(
        "-a", "--article", help="article to build (default: all)"
    )
    parser_build.add_argument(
        "-l", "--language", default="en", help="language to use (default: en)"
    )
    parser_build.add_argument(
        "target_args",
        metavar="arg",
        nargs="*",
        help="target-specific arguments",
    )

    return parser, commands.choices


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
