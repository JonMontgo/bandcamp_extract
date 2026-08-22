import click

from .commands import api, cp, extract, mv


@click.group()
def cli() -> None:
    pass


cli.add_command(extract, name="extract")
cli.add_command(api, name="api")
cli.add_command(mv, name="mv")
cli.add_command(cp, name="cp")
