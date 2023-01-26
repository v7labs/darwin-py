__all__ = ["main"]

import getpass
import os
import platform
from argparse import ArgumentParser, Namespace
from datetime import datetime
from json import dumps

import requests.exceptions

import darwin.cli_functions as f
from darwin import __version__
from darwin.exceptions import InvalidTeam, Unauthenticated, Unauthorized
from darwin.options import Options


def main() -> None:
    """
    Executes the main function of program.

    Raises
    ------
    Unauthorized
        If the API key with which the use is authenticated does not grant access for the given
        action.
    Unauthenticated
        If a given action needs authentication and you are not authenticated.
    InvalidTeam
        If you are trying to use a team that is not specified in the configuration file. To fix this
        please authenticate with the given team first.
    requests.exceptions.ConnectionError
        If there is a connection issue.
    """
    args, parser = Options().parse_args()
    try:
        _run(args, parser)
    except Unauthorized:
        f._error("Your API key is not authorized to do that action.")
    except Unauthenticated:
        f._error("You need to specify a valid API key to do that action.")
    except InvalidTeam:
        f._error("The team specified is not in the configuration, please authenticate first.")
    except requests.exceptions.ConnectionError:
        f._error("Darwin seems unreachable, please try again in a minute or contact support.")
    except Exception as e:  # Catch unhandled exceptions
        filename = f"darwin_error_{datetime.now().timestamp()}.log"

        fd = open(filename, "w")
        fd.write("Darwin CLI error log")
        fd.write(f"Version: {__version__}")
        fd.write(f"OS: {platform.platform()}")
        fd.write(f"Command: {dumps(args, check_circular=True)}")
        fd.write(f"Error: {dumps(e, check_circular=True)}")
        fd.close()

        f._error(
            "An unexpected error occurred, errors have been written to {filename}, please contact support, and send them the file."
            + str(e)
        )


def _run(args: Namespace, parser: ArgumentParser) -> None:
    if args.command == "help":
        f.help(parser)

    # Authenticate user
    if args.command == "authenticate":
        api_key = os.getenv("DARWIN_API_KEY")
        if api_key:
            print("Using API key from DARWIN_API_KEY")
        else:
            api_key = getpass.getpass(prompt="API key: ", stream=None)
            api_key = api_key.strip()
            if api_key == "":
                print("API Key needed, generate one for your team: https://darwin.v7labs.com/?settings=api-keys")
                return
        f.authenticate(api_key)
        print("Authentication succeeded.")
    # Select / List team
    elif args.command == "team":
        if args.team_name:
            f.set_team(args.team_name)
        elif args.current:
            f.current_team()
        else:
            f.list_teams()
    # Set compression level
    elif args.command == "compression":
        f.set_compression_level(args.compression_level)
    # Version
    elif args.command == "version":
        print(__version__)

    elif args.command == "convert":
        f.convert(args.format, args.files, args.output_dir)
    elif args.command == "dataset":
        if args.action == "remote":
            f.list_remote_datasets(args.all, args.team)
        elif args.action == "local":
            f.local(args.team)
        elif args.action == "create":
            f.create_dataset(args.dataset)
        elif args.action == "path":
            path = f.path(args.dataset)
            if path:
                print(path)
        # Print the url of a remote project
        elif args.action == "url":
            f.url(args.dataset)
        elif args.action == "push":
            f.upload_data(
                args.dataset,
                args.files,
                args.exclude,
                args.fps,
                args.path,
                args.frames,
                args.extract_views,
                args.preserve_folders,
                args.verbose,
            )
        # Remove a project (remotely)
        elif args.action == "remove":
            f.remove_remote_dataset(args.dataset)
        elif args.action == "report":
            f.dataset_report(args.dataset, args.granularity or "day", args.pretty)
        elif args.action == "export":
            f.export_dataset(
                args.dataset, args.include_url_token, args.name, args.class_ids, args.include_authorship, args.version
            )
        elif args.action == "files":
            f.list_files(args.dataset, args.status, args.path, args.only_filenames, args.sort_by)
        elif args.action == "releases":
            f.dataset_list_releases(args.dataset)
        elif args.action == "pull":
            f.pull_dataset(args.dataset, args.only_annotations, args.folders, args.video_frames, args.force_slots)
        elif args.action == "import":
            f.dataset_import(args.dataset, args.format, args.files, args.append, not args.yes, args.delete_for_empty)
        elif args.action == "convert":
            f.dataset_convert(args.dataset, args.format, args.output_dir)
        elif args.action == "set-file-status":
            f.set_file_status(args.dataset, args.status, args.files)
        elif args.action == "delete-files":
            f.delete_files(args.dataset, args.files, args.yes)
        elif args.action == "split":
            f.split(args.dataset, args.val_percentage, args.test_percentage, args.seed)
        elif args.action == "help" or args.action is None:
            f.help(parser, "dataset")
        elif args.action == "comment":
            f.post_comment(
                args.dataset,
                args.file,
                args.text,
                args.x,
                args.y,
                args.w,
                args.h,
            )
    # Annotation schema validation
    elif args.command == "validate":
        f.validate_schemas(location=args.location, pattern=args.pattern, silent=args.silent, output=args.output)


if __name__ == "__main__":
    main()
