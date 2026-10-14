from rich.console import Console
from rich.table import Table
from rich.panel import Panel


console = Console()


def header(title: str):
    console.print(
        Panel(title, expand=False)
    )


def indicators_table(items):
    table = Table(title="Indicators")

    table.add_column("#")
    table.add_column("Name")
    table.add_column("Identifier")

    for index, item in enumerate(items, 1):
        table.add_row(
            str(index),
            item["display_name"],
            item["identifier"],
        )

    console.print(table)


def instances_table(items):
    table = Table(title="Instances")

    table.add_column("#")
    table.add_column("Instance")
    table.add_column("Status")

    for index, item in enumerate(items, 1):

        status = item["status"]

        if status == "active":
            status = "[green]ACTIVE[/green]"
        elif status == "disabled":
            status = "[yellow]DISABLED[/yellow]"

        table.add_row(
            str(index),
            item["instance_id"],
            status,
        )

    console.print(table)
