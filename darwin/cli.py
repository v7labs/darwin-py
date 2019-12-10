import argparse
import getpass

import requests.exceptions

import darwin.cli_functions as f
from darwin.exceptions import Unauthenticated, Unauthorized
from darwin.options import Options
from darwin.utils import prompt


def main():
    args, parser = Options().parse_args()
    try:
        run(args, parser)
    except Unauthorized:
        f._error("Your API key is not authorized to do that action")
    except Unauthenticated:
        f._error("You need to specify a valid API key to do that action")
    except requests.exceptions.ConnectionError:
        f._error("Darwin seems unreachable, please try again in a minute or contact support")


def run(args, parser):
    if args.command == "help":
        print(parser.description)
        print("\nCommands:")
        subparsers_actions = [
            action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
        ]
        for subparsers_action in subparsers_actions:
            # get all subparsers and print help
            for choice in sorted(subparsers_action._choices_actions, key=lambda x: x.dest):
                print("    {:<19} {}".format(choice.dest, choice.help))

    # Authenticate user
    if args.command == "authenticate":
        api_key = getpass.getpass(prompt="API key: ", stream=None)
        if api_key.strip() == "":
            print(
                "API Key needed, generate one for your team: https://darwin.v7labs.com/?settings=api-keys"
            )
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

    # List existing projects
    elif args.command == "local":
        f.local()

    # Download dataset
    elif args.command == "pull":
        project_name = args.project_name
        local_dataset = f.pull_project(project_name)
        print(f"Project {project_name} downloaded at {local_dataset.local_path}. ")

    # Version
    elif args.command == "version":
        print("0.3")

    elif args.command == "dataset":
        # List existing projects (remotely)
        if args.action == "remote":
            f.remote(args.all, args.team)
        elif args.action == "create":
            f.create_dataset(args.dataset_name, args.team)
        elif args.action == "path":
            path = f.path(args.dataset_slug)
            print(path)
        # Print the url of a remote project
        elif args.action == "url":
            f.url(args.dataset_slug)
        elif args.action == "push":
            f.upload_data(args.dataset_slug, args.files, args.exclude, args.fps)
            # Remove a project (remotely)
        elif args.action == "remove":
            f.remove_remote_dataset(args.dataset_slug)
        elif args.action == "report":
            f.dataset_report(args.dataset_slug, args.granularity or "day")
        elif args.action == "help   ":
            dataset_parser = [
                action.choices["dataset"]
                for action in parser._actions
                if isinstance(action, argparse._SubParsersAction) and "dataset" in action.choices
            ][0]

            subparsers_actions = [
                action
                for action in dataset_parser._actions
                if isinstance(action, argparse._SubParsersAction)
            ]

            print(dataset_parser.description)
            print("\nCommands:")
            for subparsers_action in subparsers_actions:
                # get all subparsers and print help
                for choice in sorted(subparsers_action._choices_actions, key=lambda x: x.dest):
                    print("    {:<19} {}".format(choice.dest, choice.help))


if __name__ == "__main__":
    main()
