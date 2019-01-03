"""Command-line interface for Zendown."""

import argparse

from zendown.files import create_project, get_target_file, get_target_names
from zendown.build import build_target


def command_new(args):
    print(f"Creating a new Zendown project in {args.name}/")
    create_project(".", args.name)


def command_list(args):
    print("The following targets are available:\n")
    print("\n".join(get_target_names()))


def command_build(args):
    print(f"Building target {args.target}")
    build_target(args.target, args.article, args.language, args.target_args)


def get_parser():
    parser = argparse.ArgumentParser(
        prog="zendown", description="tool for building Zendown projects"
    )
    subparsers = parser.add_subparsers(
        metavar="COMMAND", dest="command", required=True
    )

    parser_new = subparsers.add_parser("new", help="create a new project")
    parser_new.add_argument("name", help="project name")

    parser_list = subparsers.add_parser("list", help="list build targets")

    parser_build = subparsers.add_parser("build", help="build the project")
    parser_build.add_argument("target", help="target to build")
    parser_build.add_argument(
        "-a", "--article", help="article to build (default: all)"
    )
    parser_build.add_argument(
        "-l", "--language", default="en", help="language to use (default: en)"
    )
    parser_build.add_argument(
        "target_args",
        metavar="ARG",
        nargs="*",
        help="target-specific arguments",
    )

    return parser


def main():
    """Entry point of the program."""
    parser = get_parser()
    args = parser.parse_args()
    command = globals()[f"command_{args.command}"]
    assert command, "unexpected command name"
    command(args)
