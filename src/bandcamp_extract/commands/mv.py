import click

from ..extract import move_to_pattern
from .options import no_track_padding_option, pattern_option, replacement_text_option


@click.command()
@click.argument("src_dir", type=click.Path(file_okay=False))
@pattern_option
@no_track_padding_option
@replacement_text_option
def mv(src_dir: str, pattern: str, no_track_padding: bool, replacement_text: str) -> None:
    move_to_pattern(src_dir, pattern, pad_track_numbers=not no_track_padding, replacement_text=replacement_text)
