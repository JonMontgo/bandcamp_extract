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

## Setup
After installation the extractor's binary is called `bcextr`.

> **Breaking change (0.2.0):** `bcextr` is now a command group. What used to be
> `bcextr <zip>` is now `bcextr extract <zip>`.

`bcextr extract` works standalone with no setup. The `bcextr api` commands
pull albums directly from your Bandcamp collection, which requires a one-time
login first.

Bandcamp has no username/password API, so this reuses the same session cookie
your browser already has after you log in on bandcamp.com.

### 1. Get your Bandcamp username
This is the name in the URL of your own collection page:
`https://bandcamp.com/<username>`. You can find it in the account menu on
bandcamp.com, or from the URL after clicking "Collection".

### 2. Get your `identity` cookie
1. Log in to bandcamp.com in your browser.
2. Open developer tools (`F12`, or `Cmd+Opt+I` on macOS).
3. Go to the **Application** tab in Chrome/Edge (**Storage** tab in Firefox),
   then **Cookies** → `https://bandcamp.com` in the left sidebar.
4. Find the row named `identity` and copy its **Value** column. It's a long
   opaque string — copy the whole thing.

This cookie is a live login credential for your account: don't share it,
paste it into chat tools, or commit it anywhere. bcextr only stores it
locally in `~/.config/bcextr/session.json` (readable only by you).

### 3. Log in with bcextr
```sh
bcextr api login
```
You'll be prompted for your Bandcamp username and the cookie value from the
steps above.

If your cookie later expires, just re-run `bcextr api login` with a fresh
value.

### Shell completion (optional)
`bcextr` is built on [Click](https://click.palletsprojects.com/), which
provides tab-completion for subcommands (`extract`, `api`, `mv`, etc.) and
file/directory paths (including for `--pattern`, which completes like a
regular folder path). Add the line for your shell to its startup file, then
restart your shell (or `source` the file):

**bash** (`~/.bashrc`):
```sh
eval "$(_BCEXTR_COMPLETE=bash_source bcextr)"
```

**zsh** (`~/.zshrc`):
```sh
eval "$(_BCEXTR_COMPLETE=zsh_source bcextr)"
```

**fish**: generate the completion file once (no eval-on-startup needed):
```sh
_BCEXTR_COMPLETE=fish_source bcextr > ~/.config/fish/completions/bcextr.fish
```

## Usage

### `bcextr extract`
Extract a zip you already downloaded:
```sh
bcextr extract ~/Downloads/album.zip --pattern ~/Music/{artist}/{album}/{title}
```
Default pattern if not provided is: `./{artist}/{album}/{title}`

### `bcextr api list` / `bcextr api choose`
List your collection:
```sh
bcextr api list
```

Pick albums and extract them straight to your library:
```sh
bcextr api choose --pattern ~/Music/{albumartist}/{album}/{title} --format flac
```
This opens an `fzf` multi-select over your collection, downloads each chosen
album in the requested format, and runs it through the same extract/rename
logic as `bcextr extract`.

`--format` accepts one of `mp3-320`, `mp3-v0`, `flac`, `aac-hi`, `vorbis`,
`alac`, `wav`, `aiff-lossless`. If omitted, you'll get a format picker
(applied to the whole batch) instead.

This relies on Bandcamp's unofficial, undocumented collection API and may
break if Bandcamp changes it.

### `bcextr mv` / `bcextr cp`
Reorganize an existing folder of music (searched recursively, however deep the
files are nested) into a pattern-based structure. `mv` moves the files (the
originals are gone); `cp` copies them, leaving the originals in place:
```sh
bcextr mv ~/Music --pattern ~/New_Music/{albumartist}/{album}/{title}
bcextr cp ~/Music --pattern ~/New_Music/{albumartist}/{album}/{title}
```

### Pattern substitution
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

It is important to note that any files that are not music (in the zip, or in the
source folder for `bcextr mv`/`bcextr cp`) are not moved or copied to the
destination folder.

### Path-unsafe symbols in metadata
Before substitution, every metadata value is run through
[pathvalidate](https://github.com/thombashi/pathvalidate)'s `replace_symbol` to
strip characters that would otherwise break the destination path (e.g. `/`,
`:`, `?`). By default these are removed entirely and spaces are left alone;
pass `--replacement-text` to substitute something else instead, and
`--strip-spaces` to also replace spaces:
```sh
bcextr extract ~/Downloads/album.zip --pattern ~/Music/{artist}/{album}/{title} --replacement-text "_" --strip-spaces
```
