import sys
from argparse import ArgumentParser, Namespace
from datetime import datetime
from typing import Any, Optional, Tuple

import argcomplete
from darwin.datatypes import AnnotatorReportGrouping


class Options:
    """
    Has functions to parse CLI options given by the user.
    """

    def __init__(self) -> None:
        self.parser: ArgumentParser = ArgumentParser(
            description="Command line tool to create/upload/download datasets on darwin."
        )

        subparsers = self.parser.add_subparsers(dest="command")
        subparsers.add_parser("help", help="Show this help message and exit.")

        # AUTHENTICATE
        auth = subparsers.add_parser("authenticate", help="Authenticate the user. ")
        auth.add_argument("--api_key", type=str, help="API key to use.")
        auth.add_argument("--default_team", type=str, help="Default team to use.")
        auth.add_argument("--datasets_dir", type=str, help="Folder to store datasets.")

        # SET COMPRESSION LEVEL
        parser_compression = subparsers.add_parser(
            "compression", help="Set compression level."
        )
        parser_compression.add_argument(
            "compression_level",
            type=int,
            choices=range(0, 10),
            help="Compression level to use on uploaded data. 0 is no compression, 9 is the best.",
        )

        # SELECT TEAM
        parser_create = subparsers.add_parser("team", help="List or pick teams.")
        parser_create.add_argument(
            "team_name", nargs="?", type=str, help="Team name to use."
        )
        parser_create.add_argument(
            "-c",
            "--current",
            action="store_true",
            required=False,
            help="Shows only the current team.",
        )

        parser_convert = subparsers.add_parser(
            "convert", help="Converts darwin json to other annotation formats."
        )
        parser_convert.add_argument(
            "format", type=str, help="Annotation format to convert to."
        )
        parser_convert.add_argument(
            "files",
            type=str,
            nargs="+",
            help="Annotation files (or folders) to convert.",
        )
        parser_convert.add_argument(
            "output_dir", type=str, help="Where to store output files."
        )

        # VALIDATE SCHEMA
        parser_validate_schema = subparsers.add_parser(
            "validate", help="Validate annotation files against Darwin schema"
        )
        parser_validate_schema.add_argument(
            "location",
            help="Location of file/folder to validate. Accepts single files or a folder to search *.json files",
        )
        parser_validate_schema.add_argument(
            "--pattern",
            action="store_true",
            help="'location' is a Folder + File glob style pattern to search (eg: ./*.json)",
        )

        parser_validate_schema.add_argument(
            "--silent",
            action="store_true",
            help="Flag to suppress all output except errors to console",
        )
        parser_validate_schema.add_argument(
            "--output", help="name of file to write output json to"
        )
        # DATASET
        dataset = subparsers.add_parser(
            "dataset",
            help="Dataset related functions.",
            description="Arguments to interact with datasets",
        )
        dataset_action = dataset.add_subparsers(dest="action")

        # Remote
        parser_remote = dataset_action.add_parser(
            "remote", help="List remote datasets."
        )
        parser_remote.add_argument("-t", "--team", help="Specify team.")
        parser_remote.add_argument(
            "-a", "--all", action="store_true", help="List datasets for all teams."
        )

        # Local
        parser_local = dataset_action.add_parser(
            "local", help="List downloaded datasets."
        )
        parser_local.add_argument("-t", "--team", help="Specify team.")

        # Create
        parser_create = dataset_action.add_parser(
            "create", help="Creates a new dataset on darwin."
        )
        parser_create.add_argument("dataset", type=str, help="Dataset name.")

        # Path
        parser_path = dataset_action.add_parser(
            "path", help="Print local path to dataset."
        )
        parser_path.add_argument("dataset", type=str, help="Dataset name.")

        # Url
        parser_url = dataset_action.add_parser(
            "url", help="Print url to dataset on darwin."
        )
        parser_url.add_argument("dataset", type=str, help="Dataset name.")

        # Push
        parser_push = dataset_action.add_parser(
            "push", help="Upload data to an existing (remote) dataset."
        )
        parser_push.add_argument(
            "dataset",
            type=str,
            help="[Remote] Dataset name: to list all the existing dataset, run 'darwin dataset remote'.",
        )
        parser_push.add_argument("files", type=str, nargs="+", help="Files to upload.")
        parser_push.add_argument(
            "-e",
            "--exclude",
            type=str,
            nargs="+",
            default="",
            help="Excludes the files with the specified extension/s if a data folder is provided as data path.",
        )
        parser_push.add_argument(
            "-f",
            "--fps",
            default="native",
            help="Frames per second for video split (recommended: 1), use 'native' to use the videos intrinsic fps.",
        )
        parser_push.add_argument(
            "--frames",
            action="store_true",
            help="Annotate a video as independent frames.",
        )

        parser_push.add_argument(
            "--extract_views",
            action="store_true",
            help="Upload a volume with all 3 orthogonal views.",
        )
        parser_push.add_argument(
            "--handle_as_slices",
            action="store_true",
            help="Upload DICOM files as slices",
        )

        parser_push.add_argument(
            "--path", type=str, default=None, help="Folder to upload the files into."
        )

        parser_push.add_argument(
            "--verbose", action="store_true", help="Flag to show upload details."
        )

        parser_push.add_argument(
            "-p",
            "--preserve-folders",
            action="store_true",
            help="Preserve the local folder structure in the dataset.",
        )
        parser_push.add_argument(
            "--item-merge-mode",
            type=str,
            choices=["slots", "series", "channels"],
            help="Specify the item merge mode: `slots`, `series`, or `channels`",
        )

        # Remove
        parser_remove = dataset_action.add_parser(
            "remove", help="Remove a remote or remote and local dataset."
        )
        parser_remove.add_argument(
            "dataset", type=str, help="Remote dataset name to delete."
        )

        # Report
        parser_report = dataset_action.add_parser(
            "report", help="Report about the annotators."
        )
        parser_report.add_argument(
            "dataset", type=str, help="Remote dataset name to report on."
        )
        parser_report.add_argument(
            "-g",
            "--granularity",
            choices=["day", "week", "month", "total"],
            help="Granularity of the report.",
        )
        parser_report.add_argument(
            "-r",
            "--pretty",
            action="store_true",
            default=False,
            help="Prints the results formatted in a rich table.",
        )
        # Export
        parser_export = dataset_action.add_parser(
            "export", help="Export a version of a dataset."
        )
        parser_export.add_argument(
            "dataset", type=str, help="Remote dataset name to export."
        )
        parser_export.add_argument(
            "name", type=str, help="Name with with the version gets tagged."
        )
        parser_export.add_argument(
            "--class-ids",
            type=str,
            nargs="+",
            help=(
                "List of annotation class ids. If present, it will only include items that have"
                " annotations with a class whose id matches."
            ),
        )
        parser_export.add_argument(
            "--include-authorship",
            default=False,
            action="store_true",
            help="Each annotation contains annotator and reviewer authorship metadata.",
        )
        parser_export.add_argument(
            "--include-url-token",
            default=False,
            action="store_true",
            help="Each annotation file includes a url with an access token. "
            "Warning, anyone with the url can access the images, even without being a team member.",
        )
        parser_export.add_argument(
            "--version",
            default=None,
            type=str,
            choices=["1.0", "2.0"],
            help="When used for V2 dataset, allows to force generation of either Darwin JSON 1.0 (Legacy) or newer 2.0. "
            "Omit this option to get your team's default.",
        )

        # Releases
        parser_dataset_version = dataset_action.add_parser(
            "releases", help="Available version of a dataset."
        )
        parser_dataset_version.add_argument(
            "dataset", type=str, help="Remote dataset name to list."
        )

        # Pull
        parser_pull = dataset_action.add_parser(
            "pull", help="Download a version of a dataset."
        )
        parser_pull.add_argument(
            "dataset", type=str, help="Remote dataset name to download."
        )
        parser_pull.add_argument(
            "--only-annotations",
            action="store_true",
            help="Download only annotations and no corresponding images.",
        )
        parser_pull.add_argument(
            "--folders",
            action="store_true",
            default=True,
            help="Recreates image folders.",
        )
        parser_pull.add_argument(
            "--no-folders",
            action="store_true",
            help="Does not recreate image folders.",
        )
        parser_pull.add_argument(
            "--video-frames",
            action="store_true",
            help="Pulls video frame images instead of video files.",
        )
        parser_pull.add_argument(
            "--retry",
            action="store_true",
            default=False,
            help="Repeatedly try to download the release if it is still processing.",
        )
        parser_pull.add_argument(
            "--retry-timeout",
            type=int,
            default=600,
            help="Total time to wait for the release to be ready for download.",
        )
        parser_pull.add_argument(
            "--retry-interval",
            type=int,
            default=10,
            help="Time to wait between retries of checking if the release is ready for download.",
        )
        slots_group = parser_pull.add_mutually_exclusive_group()
        slots_group.add_argument(
            "--force-slots",
            action="store_true",
            help="Forces pull of all slots of items into deeper file structure ({prefix}/{item_name}/{slot_name}/{file_name}). "
            + "If your dataset includes items with multiple slots, or multiple source files per slot, this option becomes implicitly enabled.",
        )
        slots_group.add_argument(
            "--ignore-slots",
            action="store_true",
            help="Ignores slots and only pulls the first slot of each item into a flat file structure ({prefix}/{file_name}).",
        )

        # Import
        parser_import = dataset_action.add_parser(
            "import", help="Import data to an existing (remote) dataset."
        )
        parser_import.add_argument(
            "dataset",
            type=str,
            help="[Remote] Dataset name: to list all the existing dataset, run 'darwin dataset remote'.",
        )
        parser_import.add_argument(
            "format", type=str, help="The format of the annotations to import."
        )
        parser_import.add_argument(
            "files",
            type=str,
            nargs="+",
            help="The location of the annotation files, or the folder where the annotation files are.",
        )
        parser_import.add_argument(
            "--append",
            action="store_true",
            help="Append annotations instead of overwriting.",
        )
        parser_import.add_argument(
            "--yes",
            action="store_true",
            help="Skips prompts for creating and adding classes to dataset.",
        )
        parser_import.add_argument(
            "--delete-for-empty",
            action="store_true",
            help="Empty annotations will delete annotations from remote files.",
        )
        parser_import.add_argument(
            "--import-annotators",
            action="store_true",
            help="Import annotators metadata from the annotation files, where available",
        )
        parser_import.add_argument(
            "--import-reviewers",
            action="store_true",
            help="Import reviewers metadata from the annotation files, where available",
        )
        parser_import.add_argument(
            "--overwrite",
            action="store_true",
            help="Bypass warnings about overwiting existing annotations.",
        )

        # Cpu limit for multiprocessing tasks
        def cpu_default_types(input: Any) -> Optional[int]:  # type: ignore
            try:
                return int(input)
            except TypeError:
                return None

        parser_import.add_argument(
            "--cpu-limit",
            "--cpu_limit",
            type=cpu_default_types,
            required=False,
            default=1,
            help="Limits amount of cores used on machine to process results, default to single core",
        )

        # Convert
        parser_convert = dataset_action.add_parser(
            "convert", help="Converts darwin json to other annotation formats."
        )
        parser_convert.add_argument(
            "dataset",
            type=str,
            help="[Remote] Dataset name: to list all the existing dataset, run 'darwin dataset remote'.",
        )
        parser_convert.add_argument(
            "format", type=str, help="Annotation format to convert to."
        )
        parser_convert.add_argument(
            "-o", "--output_dir", type=str, help="Where to store output files."
        )

        # Split
        parser_split = dataset_action.add_parser(
            "split",
            help="Splits a local dataset following random and stratified split types.",
        )
        parser_split.add_argument(
            "dataset", type=str, help="Local dataset name to split."
        )
        parser_split.add_argument(
            "-v",
            "--val-percentage",
            required=True,
            type=float,
            help="Validation percentage.",
        )
        parser_split.add_argument(
            "-t",
            "--test-percentage",
            required=True,
            type=float,
            help="Test percentage.",
        )
        parser_split.add_argument(
            "-s", "--seed", type=int, required=False, default=0, help="Split seed."
        )

        # List Files
        parser_files = dataset_action.add_parser(
            "files", help="Lists file in a remote dataset."
        )
        parser_files.add_argument(
            "dataset",
            type=str,
            help="[Remote] Dataset name: to list all the existing dataset, run 'darwin dataset remote'.",
        )
        parser_files.add_argument(
            "--only-filenames", action="store_true", help="Only prints out filenames."
        )
        parser_files.add_argument(
            "--status",
            type=str,
            required=False,
            help="Comma separated list of statuses.",
        )
        parser_files.add_argument(
            "--path",
            type=str,
            required=False,
            help="List only files under PATH. This is useful if your dataset has a directory structure.",
        )
        parser_files.add_argument(
            "--sort-by",
            type=str,
            required=False,
            help="Sort remotely fetched files by the given direction. Defaults to 'updated_at:desc'.",
        )

        # Set file status
        parser_file_status = dataset_action.add_parser(
            "set-file-status", help="Sets the status of one or more files."
        )
        parser_file_status.add_argument(
            "dataset",
            type=str,
            help="[Remote] Dataset name: to list all the existing dataset, run 'darwin dataset remote'.",
        )
        parser_file_status.add_argument("status", type=str, help="Status to change to.")
        parser_file_status.add_argument(
            "files", type=str, nargs="+", help="Files to change status."
        )

        # Delete files
        parser_delete_files = dataset_action.add_parser(
            "delete-files", help="Delete one or more files remotely."
        )
        parser_delete_files.add_argument(
            "dataset",
            type=str,
            help="[Remote] Dataset name: to list all the existing dataset, run 'darwin dataset remote'.",
        )
        parser_delete_files.add_argument(
            "files", type=str, nargs="+", help="Files to delete."
        )
        parser_delete_files.add_argument(
            "-y",
            "--yes",
            default=False,
            action="store_true",
            required=False,
            help="Confirmation flag to delete the file without prompting for manual input.",
        )

        # Add comments
        parser_comment = dataset_action.add_parser("comment", help="Comment image.")
        parser_comment.add_argument(
            "dataset",
            type=str,
            help="[Remote] Dataset name: to list all the existing dataset, run 'darwin dataset remote'. ",
        )
        parser_comment.add_argument("file", type=str, help="File to comment")
        parser_comment.add_argument(
            "--text", type=str, help="Comment: list of words", required=True
        )
        parser_comment.add_argument(
            "--x",
            required=False,
            type=float,
            default=1,
            help="X coordinate for comment box",
        )
        parser_comment.add_argument(
            "--y",
            required=False,
            type=float,
            default=1,
            help="Y coordinate for comment box",
        )
        parser_comment.add_argument(
            "--w",
            "--width",
            required=False,
            type=float,
            default=1,
            help="Comment box width in pixels",
        )
        parser_comment.add_argument(
            "--h",
            "--height",
            required=False,
            type=float,
            default=1,
            help="Comment box height in pixels",
        )

        # Help
        dataset_action.add_parser("help", help="Show this help message and exit.")

        # REPORT
        report = subparsers.add_parser(
            "report",
            help="Report related functions.",
            description="Arguments to interact with reports",
        )
        report_action = report.add_subparsers(dest="action")

        # Annotators
        parser_annotators = report_action.add_parser(
            "annotators", help="Report about the annotators."
        )
        parser_annotators.add_argument(
            "--datasets",
            default=[],
            type=lambda csv: [value.strip() for value in csv.split(",")],
            help="List of comma-separated dataset slugs to include in the report.",
        )
        parser_annotators.add_argument(
            "--start",
            required=True,
            type=lambda dt: datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S%z"),
            help="Report start DateTime in RFC3339 format (e.g. 2020-01-20T14:00:00Z).",
        )
        parser_annotators.add_argument(
            "--stop",
            required=True,
            type=lambda dt: datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S%z"),
            help="Report end DateTime in RFC3339 format (e.g. 2020-01-20T15:00:00Z).",
        )
        parser_annotators.add_argument(
            "--group-by",
            required=True,
            type=lambda csv: [value.strip() for value in csv.split(",")],
            help=f"Non-empty list of comma-separated grouping options for the report, any of: f{[name.value for name in AnnotatorReportGrouping]}.",
        )
        parser_annotators.add_argument(
            "-r",
            "--pretty",
            action="store_true",
            default=False,
            help="Prints the results formatted in a rich table.",
        )

        # VERSION
        subparsers.add_parser(
            "version", help="Check current version of the repository. "
        )

        # EXTRACTION
        parser_extract = subparsers.add_parser(
            "extract", help="Extract and process media files"
        )
        extract_subparsers = parser_extract.add_subparsers(dest="extract_type")

        # Video artifacts
        parser_video = extract_subparsers.add_parser(
            "video-artifacts",
            help="Extract video artifacts for read-only registration in the Darwin platform",
            description="Process video files to generate streaming artifacts including HLS segments, "
            "thumbnails, frame extracts, and manifest files required for video playback "
            "in the V7 Darwin platform.",
        )
        parser_video.add_argument(
            "source_file",
            type=str,
            help="Path to input video file",
        )
        parser_video.add_argument(
            "-p",
            "--storage-key-prefix",
            type=str,
            required=True,
            help="Storage key prefix for generated files",
        )
        parser_video.add_argument(
            "-o",
            "--output-dir",
            type=str,
            required=True,
            help="Output directory for artifacts",
        )
        parser_video.add_argument(
            "-f",
            "--fps",
            type=float,
            default=0.0,
            help="Desired output FPS (0.0 for native)",
        )
        parser_video.add_argument(
            "-s",
            "--segment-length",
            type=int,
            default=2,
            help="Length of each segment in seconds",
        )
        parser_video.add_argument(
            "--repair",
            action="store_true",
            help="Checks video for errors and attempts to repair them",
        )

        argcomplete.autocomplete(self.parser)

    def parse_args(self) -> Tuple[Namespace, ArgumentParser]:
        """
        Parses and validates the CLI options.

        Returns
        -------
        Tuple[Namespace, ArgumentParser]
            The tuple with the namespace and parser to use.
        """
        args = self.parser.parse_args()

        if not args.command:
            self.parser.print_help()
            sys.exit()

        return args, self.parser
