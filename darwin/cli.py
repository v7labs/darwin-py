import argparse
import getpass

import darwin.cli_functions as f
from darwin.options import Options
from darwin.utils import prompt


def main():
    args, parser = Options().parse_args()

    if args.command == "help":
        print(parser.description)
        print("\nCommands:\n")
        subparsers_actions = [
            action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
        ]
        for subparsers_action in subparsers_actions:
            # get all subparsers and print help
            for choice in sorted(subparsers_action._choices_actions, key=lambda x: x.dest):
                print("    {:<19} {}".format(choice.dest, choice.help))

    # Authenticate user
    if args.command == "authenticate":
        email = input("Username (email address): ")
        password = getpass.getpass(prompt="Password: ", stream=None)
        projects_dir = prompt("Project directory", "~/.darwin/projects")
        f.authenticate(email, password, projects_dir)
        print("Authentication succeeded. ")

    # Select / List team
    elif args.command == "team":
        if args.team_name:
            f.set_team(args.team_name)
        elif args.list:
            f.list_teams()
        else:
            f.current_team()
    # Create new project
    elif args.command == "create":
        f.create_dataset(args.project_name)

    # List existing projects
    elif args.command == "local":
        f.local()

    # Print projects local path
    elif args.command == "path":
        path = f.path(args.project_name)
        print(path)

    elif args.command == "url":
        url = f.url(args.project_name)
        print(url)

    # Download dataset
    elif args.command == "pull":
        project_name = args.project_name
        local_dataset = f.pull_project(project_name)
        print(f"Project {project_name} downloaded at {local_dataset.project_path}. ")

    # List existing projects (remotely)
    elif args.command == "remote":
        f.remote()

    # Remove a project (remotely)
    elif args.command == "remove":
        project_name = args.project_name
        if args.remote:
            f.remove_remote_project(project_name)
        else:
            f.remove_local_project(project_name)

    # Upload new data to a project (remotely)
    elif args.command == "upload":
        f.upload_data(args.project_name, args.files, args.exclude, args.fps, args.recursive)

    elif args.command == "version":
        print("0.0.1")


if __name__ == "__main__":
    main()
