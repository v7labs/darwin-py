from enum import Enum, auto
from typing import Type, Union

from rich.console import Console


class OutputStyle(Enum):
    NONE = auto()
    SUCCESS = auto()
    FAILURE = auto()


class TerminalOut:
    console: Console
    SUCCESS: str
    FAILURE: str

    def __init__(self, plainterm: bool = False):
        if plainterm:
            self.console = Console(color_system=None, emoji=False, width=80)
            self.SUCCESS = "✔︎"
            self.FAILURE = "✕"
        else:
            self.console = Console(
                width=80,
            )
            self.SUCCESS = "✅"
            self.FAILURE = "❌"

    def newline(self) -> None:
        self.console.print()

    def section(self, name: str) -> None:
        self.console.rule(f"[cyan]{name}[/cyan]")

    def message(self, message: str, icon: Union[str, None] = None) -> None:
        self.__print_output_message(message, icon if icon else "", self.console)

    def success(self, message: str) -> None:
        self.__print_output_message(message, self.SUCCESS, self.console, OutputStyle.SUCCESS)

    def fail(self, message: str) -> None:
        self.__print_output_message(message, self.FAILURE, self.console, OutputStyle.FAILURE)

    def __print_output_message(
        self, message: str, icon: str, console: Console, output_style: OutputStyle = OutputStyle.NONE
    ) -> None:
        if output_style == OutputStyle.SUCCESS:
            self.console.print(f"[green]{message}[/green]")
        elif output_style == OutputStyle.FAILURE:
            self.console.print(f"[red]{message}[/red]")
        else:
            self.console.print(message)

        if icon:
            self.console.print(icon, new_line_start=False, justify="right")
