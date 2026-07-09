import click

from .commands.api import api
from .commands.cp import cp
from .commands.extract import extract
from .commands.mv import mv


@click.group()
def cli() -> None:
    pass


cli.add_command(extract, name="extract")
cli.add_command(api, name="api")
cli.add_command(mv, name="mv")
cli.add_command(cp, name="cp")
