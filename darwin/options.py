import argparse
import sys

import argcomplete


class Options(object):
    def __init__(self):

        self.parser = argparse.ArgumentParser(
            description="Commandline tool to create/upload/download datasets on darwin."
        )

        subparsers = self.parser.add_subparsers(dest="command")
        parse_help = subparsers.add_parser("help", help="Show this help message and exit.")

        # AUTHENTICATE
        parser_authenticate = subparsers.add_parser("authenticate", help="Authenticate the user. ")

        # SELECT TEAM
        parser_create = subparsers.add_parser("team", help="List or pick teams. ")
        parser_create.add_argument("team_name", nargs="?", type=str, help="Team name to use. ")
        parser_create.add_argument(
            "-l", "--list", action="store_true", required=False, help="Lists all teams. "
        )

        # PROJECT CREATE
        parser_create = subparsers.add_parser("create", help="Create a new project. ")
        parser_create.add_argument("project_name", type=str, help="Project name. ")

        # PROJECT LOCAL
        parser_local = subparsers.add_parser("local", help="List local projects. ")

        # PROJECT PATH
        parser_path = subparsers.add_parser(
            "path", help="Prints absolute path of a local project. "
        )
        parser_path.add_argument("project_name", help="Name of the local project. ")

        # PROJECT URL
        parser_url = subparsers.add_parser("url", help="Prints the url of a remote project. ")
        parser_url.add_argument("project_name", help="Name of the remote project. ")

        # PROJECT PULL
        parser_pull = subparsers.add_parser(
            "pull", help="Pull/Download an existing remote project. "
        )
        parser_pull.add_argument("project_name", type=str, help="Dataset output name. ")

        # PROJECT REMOTE
        parser_remote = subparsers.add_parser("remote", help="List remote projects. ")

        # PROJECT REMOVE
        parser_remove = subparsers.add_parser(
            "remove", help="Remove a remote or remote and local projects. "
        )
        parser_remove.add_argument("project_name", type=str, help="Remote project name to delete. ")
        parser_remove.add_argument(
            "-r",
            "--remote",
            dest="remote",
            action="store_true",
            required=False,
            help="Indicates that the project deletion should be performed on darwin. ",
        )

        # PROJECT UPLOAD
        parser_upload = subparsers.add_parser(
            "upload", help="Upload data to an existing (remote) project. "
        )
        parser_upload.add_argument(
            "project_name",
            type=str,
            help="[Remote] Project name: to list all the existing projects, type 'darwin remote'. ",
        )
        parser_upload.add_argument("files", type=str, nargs="+", help="Files to upload")
        parser_upload.add_argument(
            "-r",
            "--recursive",
            action="store_true",
            help="recursively traverse folders for files to upload",
        )

        parser_upload.add_argument(
            "-e",
            "--exclude",
            type=str,
            nargs="+",
            default="",
            help="Excludes the files with the specified extension/s if a data folder is provided as data path. ",
        )
        parser_upload.add_argument(
            "-f",
            "--fps",
            type=int,
            default="1",
            help="Frames per second for video split (recommended: 1). ",
        )

        # VERSION
        parser_version = subparsers.add_parser(
            "version", help="Check current version of the repository. "
        )

        argcomplete.autocomplete(self.parser)

    def parse_args(self):
        args = self.parser.parse_args()
        if not args.command:
            self.parser.print_help()
            sys.exit()
        return args, self.parser
