import click

from ..extract import copy_to_pattern
from .options import no_track_padding_option, pattern_option, replacement_text_option


@click.command()
@click.argument("src_dir", type=click.Path(file_okay=False))
@pattern_option
@no_track_padding_option
@replacement_text_option
def cp(src_dir: str, pattern: str, no_track_padding: bool, replacement_text: str) -> None:
    copy_to_pattern(src_dir, pattern, pad_track_numbers=not no_track_padding, replacement_text=replacement_text)
