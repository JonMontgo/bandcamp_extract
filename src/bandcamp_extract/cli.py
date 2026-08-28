import click

from .commands import api, cp, extract, mv, sync


@click.group()
@click.version_option(package_name="bandcamp_extract")
def cli() -> None:
    pass


cli.add_command(extract, name="extract")
cli.add_command(api, name="api")
cli.add_command(mv, name="mv")
cli.add_command(cp, name="cp")
cli.add_command(sync, name="sync")
