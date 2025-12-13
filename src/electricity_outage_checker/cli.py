"""CLI entry point for electricity-outage-checker."""

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .client import DTEKClient, DTEKClientError
from .config import (
    clear_default_address,
    get_default_address,
    set_default_address,
)
from .models import Address, DaySchedule, PowerStatus

app = typer.Typer(
    name="outage-checker",
    help="CLI tool to check DTEK electricity outage schedules.",
    add_completion=False,
)
console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"[bold]electricity-outage-checker[/bold] version {__version__}")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-V",
            help="Show version and exit.",
            callback=version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    """Electricity Outage Checker.

    Check DTEK electricity outage schedules from the command line.
    """


def _get_status_style(status: PowerStatus) -> str:
    """Get Rich style for a power status."""
    if status.has_power:
        return "green"
    if status.no_power:
        return "red bold"
    if status.is_uncertain:
        return "yellow"
    return "red"


def _render_schedule_table(schedule: DaySchedule, preset_translations: dict[str, str]) -> Table:
    """Render a schedule as a Rich table."""
    table = Table(
        title=f"{schedule.day_name} ({schedule.date_str}) - {schedule.group}",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Hour", style="dim", width=8)
    table.add_column("Status", width=30)

    for hour in schedule.hours:
        style = _get_status_style(hour.status)
        status_text = hour.status.get_display_text(preset_translations)
        table.add_row(hour.time_range, f"[{style}]{status_text}[/{style}]")

    return table


@app.command()
def check(
    address: Annotated[
        str | None,
        typer.Argument(
            help="Address to check (format: city, street, house). "
            "Uses default address if not provided."
        ),
    ] = None,
) -> None:
    """Check shutdown schedule for a specific address."""
    # Resolve address
    addr: Address | None = None
    if address:
        try:
            addr = Address.from_string(address)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None
    else:
        addr = get_default_address()
        if addr is None:
            # First-time user flow: prompt to set default address
            console.print(
                "[yellow]No default address configured.[/yellow]\n"
                "Would you like to set a default address now?\n"
                "[dim]This will save the address so you don't have to type it every time.[/dim]"
            )
            set_default = typer.confirm("Set default address?", default=True)

            if set_default:
                console.print(
                    "\n[cyan]Tip:[/cyan] You can use these commands to find your address:\n"
                    "  [dim]outage-checker list-cities[/dim] - List all available cities\n"
                    "  [dim]outage-checker list-streets <city>[/dim] - "
                    "List streets in a city\n"
                    "  [dim]outage-checker list-houses <city> <street>[/dim] - "
                    "List houses on a street\n"
                )
                address_input = typer.prompt(
                    "\nEnter your address (format: city, street, house)"
                )

                try:
                    addr = Address.from_string(address_input)
                except ValueError as e:
                    console.print(f"[red]Error:[/red] {e}")
                    raise typer.Exit(1) from None

                # Verify and save the address
                console.print("[dim]Verifying address...[/dim]")
                try:
                    with DTEKClient() as client:
                        group = client.fetch_address_group(addr.city, addr.street, addr.house)
                except DTEKClientError as e:
                    console.print(f"[red]Error:[/red] {e}")
                    raise typer.Exit(1) from None

                if group is None:
                    console.print(
                        f"[red]Error:[/red] Address not found: {addr}\n"
                        "Please verify the address and try again."
                    )
                    raise typer.Exit(1)

                set_default_address(addr)
                console.print(f"[green]Default address saved![/green] (Power group: {group})\n")
            else:
                console.print(
                    "\n[yellow]No problem![/yellow] "
                    "You can check any address by providing it as an argument:\n"
                    "  [cyan]outage-checker check 'city, street, house'[/cyan]\n"
                )
                raise typer.Exit(0)

    console.print(f"[dim]Checking schedule for:[/dim] [bold]{addr}[/bold]\n")

    try:
        with DTEKClient() as client:
            schedules = client.get_schedule_for_address(addr)
    except DTEKClientError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None

    if not schedules:
        console.print("[yellow]No schedule data available.[/yellow]")
        raise typer.Exit(0)

    # Get translations for status display
    translations = {
        "yes": "Power ON",
        "no": "Power OFF",
        "maybe": "Maybe OFF",
        "first": "OFF first 30 min",
        "second": "OFF second 30 min",
        "mfirst": "Maybe OFF first 30 min",
        "msecond": "Maybe OFF second 30 min",
    }

    # Display schedules as tables
    for schedule in schedules:
        table = _render_schedule_table(schedule, translations)
        console.print(table)
        console.print()


@app.command()
def set_address(
    address: Annotated[
        str,
        typer.Argument(help="Address to set as default (format: city, street, house)"),
    ],
) -> None:
    """Set the default address for schedule checks."""
    try:
        addr = Address.from_string(address)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None

    # Verify the address exists by fetching its group
    console.print("[dim]Verifying address...[/dim]")
    try:
        with DTEKClient() as client:
            group = client.fetch_address_group(addr.city, addr.street, addr.house)
    except DTEKClientError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None

    if group is None:
        console.print(
            f"[red]Error:[/red] Address not found: {addr}\nPlease verify the address is correct."
        )
        raise typer.Exit(1)

    set_default_address(addr)
    console.print(f"[green]Default address set to:[/green] {addr}")
    console.print(f"[dim]Power group:[/dim] {group}")


@app.command()
def show_address() -> None:
    """Show the currently configured default address."""
    addr = get_default_address()
    if addr is None:
        console.print("[yellow]No default address configured.[/yellow]")
        console.print("Use [cyan]shutdowns-checker set-address[/cyan] to set one.")
    else:
        console.print(f"[bold]Default address:[/bold] {addr}")


@app.command()
def clear_address() -> None:
    """Clear the default address configuration."""
    clear_default_address()
    console.print("[green]Default address cleared.[/green]")


@app.command()
def list_cities() -> None:
    """List all available cities/settlements."""
    try:
        with DTEKClient() as client:
            streets, _, _ = client.fetch_schedule_page()
    except DTEKClientError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None

    console.print("[bold]Available cities/settlements:[/bold]\n")
    for city in sorted(streets.keys()):
        console.print(f"  {city}")


@app.command()
def list_streets(
    city: Annotated[
        str,
        typer.Argument(help="City/settlement name to list streets for"),
    ],
) -> None:
    """List all available streets in a city (usage: CITY)."""
    try:
        with DTEKClient() as client:
            streets, _, _ = client.fetch_schedule_page()
    except DTEKClientError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None

    city_streets = streets.get(city)
    if city_streets is None:
        console.print(f"[red]Error:[/red] City not found: {city}")
        console.print("Use [cyan]shutdowns-checker list-cities[/cyan] to see available cities.")
        raise typer.Exit(1)

    console.print(f"[bold]Streets in {city}:[/bold]\n")
    for street in sorted(city_streets):
        console.print(f"  {street}")


@app.command()
def list_houses(
    city: Annotated[
        str,
        typer.Argument(help="City/settlement name"),
    ],
    street: Annotated[
        str,
        typer.Argument(help="Street name"),
    ],
) -> None:
    """List all available houses on a street (usage: CITY STREET)."""
    try:
        with DTEKClient() as client:
            houses = client.fetch_houses(city, street)
    except DTEKClientError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None

    if not houses:
        console.print(f"[red]Error:[/red] No houses found for: {city}, {street}")
        console.print("Use [cyan]shutdowns-checker list-streets[/cyan] to verify the street name.")
        raise typer.Exit(1)

    console.print(f"[bold]Houses on {street} ({city}):[/bold]\n")

    # Sort houses naturally (1, 2, 10, 11 instead of 1, 10, 11, 2)
    def natural_sort_key(s: str) -> list[int | str]:
        import re

        return [int(c) if c.isdigit() else c for c in re.split(r"(\d+)", s)]

    for house in sorted(houses, key=natural_sort_key):
        console.print(f"  {house}")


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
