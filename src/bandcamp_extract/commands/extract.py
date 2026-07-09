import click

from ..extract import extract_zip
from .options import no_track_padding_option, pattern_option, replacement_text_option


@click.command()
@click.argument("zip_path", type=click.Path(dir_okay=False))
@pattern_option
@no_track_padding_option
@replacement_text_option
def extract(zip_path: str, pattern: str, no_track_padding: bool, replacement_text: str) -> None:
    extract_zip(zip_path, pattern, pad_track_numbers=not no_track_padding, replacement_text=replacement_text)
