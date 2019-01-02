"""Command-line interface for Zendown."""

import argparse


def command_new():
    print("new")


def command_list():
    print("new")


def command_build():
    print("new")


def get_parser():
    parser = argparse.ArgumentParser(
        prog="zendown", description="tool for building Zendown projects")
    subparsers = parser.add_subparsers(
        metavar="COMMAND", dest="command", required=True)

    parser_new = subparsers.add_parser("new", help="create a new project")

    parser_list = subparsers.add_parser("list", help="list build targets")

    parser_build = subparsers.add_parser("build", help="build the project")
    parser_build.add_argument("target", help="target to build")

    return parser


def main():
    """Entry point of the program."""
    parser = get_parser()
    args = parser.parse_args()
    command = globals()[f"command_{args.command}"]
    assert command, "unexpected command name"
