import click

from .commands.api import api
from .commands.extract import extract


@click.group()
def cli() -> None:
    pass


cli.add_command(extract, name="extract")
cli.add_command(api, name="api")
