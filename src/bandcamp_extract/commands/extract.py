import click

from ..extract import extract_zip
from .options import no_track_padding_option, pattern_option, replacement_text_option, strip_spaces_option


@click.command()
@click.argument("zip_path", type=click.Path(dir_okay=False))
@pattern_option
@no_track_padding_option
@replacement_text_option
@strip_spaces_option
def extract(
    zip_path: str, pattern: str, no_track_padding: bool, replacement_text: str, strip_spaces: bool
) -> None:
    extract_zip(
        zip_path,
        pattern,
        pad_track_numbers=not no_track_padding,
        replacement_text=replacement_text,
        strip_spaces=strip_spaces,
    )
