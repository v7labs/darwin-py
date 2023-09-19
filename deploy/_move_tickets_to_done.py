#!/usr/bin/env python3

import argparse
import json
import os
import re

from confirm_main_branch_deployability import ExitCodes, _exit, _run_command

parser = argparse.ArgumentParser(description="Move tickets in release to done.")
parser.add_argument("--release-tag", "--tag", "-t", help="The release tag to move tickets from", required=True)
parser.add_argument("--dry-run", action="store_true", help="Don't actually move tickets to done")

args = parser.parse_args()
release_tag = args.release_tag

LINEAR_API_KEY = os.environ.get("LINEAR_API_KEY")

print(f"\nMoving tickets in release {release_tag} to done")

if dry_run := args.dry_run:
    print("Dry run, not actually moving tickets")

# get details
body, error = _run_command("gh", "release", "view", release_tag, "--json", "body")
assert error == 0, _exit("Failed to get last release body", ExitCodes.GETTING_RELEASE_METADATA_THREW_EXITCODE)

body_parsed = json.loads(body)
body = body_parsed["body"].split("\n")

TICKET_MATCHER = re.compile(r"^\* \[([A-z]+-[0-9]+)\]")

wrong_lines = [line for line in body if line.startswith("* ") and not TICKET_MATCHER.match(line)]
body_lines = [line.upper() for line in body if TICKET_MATCHER.match(line)]

unmoved_tickets = len(wrong_lines) - len(body_lines)
moved_tickets = len(body_lines)

print("Tickets to move to done:")
ticket_codes = []
for line in body_lines:
    ticket = TICKET_MATCHER.match(line).group(1)  # type: ignore
    print(f"  - {ticket}")
    ticket_codes.append(ticket)

if unmoved_tickets > 0:
    print("\nWARNING: Some PRs weren't properly formatted")
    print(f"There were {unmoved_tickets} PRs that weren't properly formatted")
    print("These will need moving manually.")
    print()
    [print(line) for line in wrong_lines]
    exit(232)

print("\n")

# TODO move tickets to done
if not dry_run:
    for ticket in ticket_codes:
        query = f"""
        mutation IssueUpdate {{
            issueUpdate(
                id: "{ticket}",
                input: {{
                stateId: "Done",
                }}
            ) {{
                success
                issue {{
                id
                title
                state {{
                    id
                    name
                }}
                }}
            }}
        }}"""
