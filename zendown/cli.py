"""Command-line interface."""

import logging
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Mapping, Tuple

from zendown.build import Options, builders
from zendown.files import create_project
from zendown.logs import setup_logging
from zendown.project import Project
from zendown.watch import Server, Watcher


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
    if args.keep_going or getattr(args, "watch", False):
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
        "queries",
        metavar="QUERY",
        nargs="*",
        default="",
        help="filter articles by ref",
    )

    parser_build = commands.add_parser("build", help="build the project")
    parser_build.add_argument("builder", choices=builders.keys(), help="build target")
    parser_build.add_argument(
        "-c", "--clean", action="store_true", help="clean the build directory first",
    )
    parser_build.add_argument(
        "-w",
        "--watch",
        action="store_true",
        help="watch files and automatically rebuild",
    )
    parser_build.add_argument(
        "-o",
        "--open",
        action="store_true",
        help="open the browser (live-reloading if --watch)",
    )
    parser_build.add_argument(
        "-p",
        "--port",
        type=int,
        default=5000,
        help="port to use for --watch --open server",
    )
    parser_build.add_argument(
        "-f", "--flat", action="store_true", help="flat (non-hierarchical) for latex"
    )
    parser_build.add_argument(
        "-t", "--top", type=str, help="part/chapter/section for latex"
    )
    parser_build.add_argument(
        "queries",
        metavar="QUERY",
        nargs="*",
        default="",
        help="filter articles by ref",
    )

    for subparser in [parser_new, parser_list, parser_build]:
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
    for article in project.queries(args.queries):
        print(article.path if args.files else article.node.ref)


def command_build(args: Namespace):
    project = Project.find()
    builder = builders[args.builder](project, Options(flat=args.flat, top=args.top))
    if args.clean:
        builder.clean()
    if args.watch:
        if not builder.supports_watch:
            logging.fatal("build target %s does not support --watch", args.builder)
        if args.queries:
            logging.warning("queries %s ignored for --watch", args.queries)
        server = None
        if args.open:
            server = Server(port=args.port, builder=builder)
        Watcher(project, builder, server).run()
    else:
        articles = project.queries(args.queries)
        builder.build(articles, open_output=args.open)
