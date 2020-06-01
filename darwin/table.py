from typing import Dict, List


class Table(object):
    """Handles table-like formatted text"""

    R = True
    L = False

    def __init__(self, columns: List[str], alignments: List[bool], column_margin: int = 5):
        if len(columns) == 0:
            raise Exception("No columns specified")
        if len(columns) != len(alignments):
            raise Exception("Columns and alignments should have the same length")
        self.alignments = alignments
        self.column_margin = column_margin
        self.table: dict = {column: [] for column in columns}
        self.default_size = 50

    def add_row(self, row: Dict):
        """Appends row to table. The function raises an Exception when the row keys do not match with table columns."""

        if list(row.keys()) != list(self.table.keys()):
            raise Exception("Specified line should have same fields as the table columns")
        for column, value in row.items():
            self.table[str(column)].append(str(value))

    def _build_header(self, sizes: List[int]) -> str:
        header = ""
        for column, size, alignment in zip(self.table.keys(), sizes, self.alignments):
            if alignment:
                header += f"{column.upper():>{size}}"
            else:
                header += f"{column.upper():<{size}}"
        return header

    def _build_row(self, row_dict: Dict[str, str], sizes: List[int]) -> str:
        row = ""
        for value, size, alignment in zip(row_dict.values(), sizes, self.alignments):
            if alignment:
                row += f"{value:>{size}}"
            else:
                row += f"{value:<{size}}"
        return row

    def __len__(self) -> int:
        return len(list(self.table.values())[0])

    def __str__(self) -> str:
        if len(self) == 0:
            return ""

        column_sizes = [len(max(self.table[column] + [column], key=len)) + self.column_margin for column in self.table]
        rows = [self._build_header(column_sizes)]
        for values in zip(*self.table.values()):
            row = {key: value for key, value in zip(self.table.keys(), values)}
            rows.append(self._build_row(row, column_sizes))
        return "\n".join(rows)
