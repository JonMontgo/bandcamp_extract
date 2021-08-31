import os
import shutil
from tinytag import TinyTag, TinyTagException
import click
import zipfile
import tempfile
import glob


@click.argument("zip_path")
@click.option(
    "--pattern",
    default=(
        f"{os.getcwd()}" +
        "/{artist}/{album}/{title}"
    ),
)
@click.command()
def extract(zip_path: str, pattern: str):
    if not zipfile.is_zipfile(zip_path):
        raise click.ClickException(f"{zip_path} is not a zip file!")
    with zipfile.ZipFile(zip_path) as zipfh:
        with tempfile.TemporaryDirectory() as tmpdirname:
            zipfh.extractall(path=tmpdirname)
            for potential_song_path in glob.glob(f"{tmpdirname}/*"):
                try:
                    song_ext = os.path.splitext(potential_song_path)[1]
                    potential_song = TinyTag.get(potential_song_path)
                    substitution_dict = potential_song.as_dict()
                    new_path = pattern.format(**substitution_dict) + song_ext
                    if not os.path.exists(os.path.dirname(new_path)):
                        os.makedirs(os.path.dirname(new_path))
                    shutil.move(potential_song_path, new_path)
                except TinyTagException:
                    pass
                except KeyError as err:
                    raise click.ClickException(
                        f"Param {{{err.args[0]}}} in pattern " +
                        f"{pattern} not found"
                    )
