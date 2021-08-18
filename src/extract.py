#!env python3
from pathlib import Path
import click


@click.argument("zip_path")
@click.option(
    "--pattern",
    default=f"{Path.home()}/Music" + "/{Artist}/{Album}/{Song}"
)
@click.command()
def extract(zip_path, pattern):
    click.echo(zip_path)
    click.echo(pattern)


# if __name__ == "__main__":
#     try:
#         file_name = sys.argv[1]
#     except IndexError:
#         raise Exception("Please provide a file name")
#     if not zipfile.is_zipfile(file_name):
#         raise Exception("File must be a .zip and found in directory.")

#     with zipfile.ZipFile(file_name, mode="r") as zfh:
#         non_songs = []
#         path_name = ""
#         for file_name in zfh.namelist():
#             matched = file_name_re.match(file_name)
#             if matched is not None:
#                 artist, album, track_number, song = matched.groups()
#                 path_name = "%s/Music/%s/%s" % (Path.home(), artist, album)
#                 if not os.path.exists(path_name):
#                     os.makedirs(path_name)
#                 file_bytes = zfh.read(file_name)
#                 with open("%s/%s %s" % (path_name, track_number, song),
#                           "wb") as fh:
#                     fh.write(file_bytes)
#             else:
#                 non_songs.append(file_name)
#         for file_name in non_songs:
#             zfh.extract(file_name, path=path_name)
#     os.remove(sys.argv[1])
