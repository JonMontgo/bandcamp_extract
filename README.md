# Band Camp Album Extractor
This python script extracts all of the songs for a bandcamp album download.

## Install

### (preferred) from pip
```sh
pip install bandcamp_extract
```

### From github repo
To install this package simply run
```sh
pip install .
```
in the root of this package

## Usage
After installation the extrator's binary is called `bcextr` it can be used like
so
```sh
bcextr ~/Downloads/album.zip --pattern ~/Music/{artist}/{album}/{title}
```
Default pattern if not provided is: `./{artist}/{album}/{title}`

The pattern substitution will substitute any parameter it gets in [tinytag](https://github.com/devsnd/tinytag)
The file extension will also be added to the end of the `pattern` when moving
the song to it's destination

```py
tag.album         # album as string
tag.albumartist   # album artist as string
tag.artist        # artist name as string
tag.audio_offset  # number of bytes before audio data begins
tag.bitrate       # bitrate in kBits/s
tag.comment       # file comment as string
tag.composer      # composer as string 
tag.disc          # disc number
tag.disc_total    # the total number of discs
tag.duration      # duration of the song in seconds
tag.filesize      # file size in bytes
tag.genre         # genre as string
tag.samplerate    # samples per second
tag.title         # title of the song
tag.track         # track number as string
tag.track_total   # total number of tracks as string
tag.year          # year or data as string
```

It is important to note that any files that are not music in the zip are not moved to the 
destination folder.
