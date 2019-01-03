"""Command-line interface for Zendown."""

import argparse
import os
import os.path


STRUCTURE = {
    "assets": {},
    "content": {"hello.txt": "Hello, world!"},
    "data": {},
    "layouts": {},
    "macros": {},
    "targets": {},
}


def command_new(args):
    def create(root, structure):
        for key, val in structure.items():
            path = os.path.join(root, key)
            if isinstance(val, dict):
                os.mkdir(path)
                create(path, val)
            else:
                assert isinstance(val, str)
                with open(path, "w") as f:
                    f.write(val)

    print(f"Creating a new Zendown project in {args.name}/")
    create(os.getcwd(), {args.name: STRUCTURE})


def command_list(args):
    print("list")


def command_build(args):
    print("builda")


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

    return parser


def main():
    """Entry point of the program."""
    parser = get_parser()
    args = parser.parse_args()
    command = globals()[f"command_{args.command}"]
    assert command, "unexpected command name"
    command(args)
