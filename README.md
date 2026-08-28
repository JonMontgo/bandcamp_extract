# BandCamp Album Extractor

Download and organize your bandcamp library with ease!

![Made with VHS](https://vhs.charm.sh/vhs-530Ye82ukIPq9ra4r8hDGf.gif)

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

In `fzf` there are two hot keys to keep in mind. `Ctrl+a` will select all and
`Tab` will toggle a selection in the list.

`--format` accepts one of `mp3-320`, `mp3-v0`, `flac`, `aac-hi`, `vorbis`,
`alac`, `wav`, `aiff-lossless`. If omitted, you'll get a format picker
(applied to the whole batch) instead.

This relies on Bandcamp's unofficial, undocumented collection API and may
break if Bandcamp changes it.

### `bcextr sync`
Incrementally synchronize your entire Bandcamp collection into your music library:
```sh
bcextr sync --pattern ~/Music/{albumartist,artist}/{album}/{track}-{title} --format flac
```

`bcextr sync` tracks your synced purchases in `~/.config/bcextr/sync.toml` (or a custom file via `--sync-file`) and
only downloads what needs updating:
- **New purchases**: downloads albums and standalone tracks added to your Bandcamp collection since the last sync.
- **Updated items**: re-downloads items whose metadata or files were modified on Bandcamp after your last sync.
- **Format changes**: re-downloads in the new format if you switch `--format` (e.g. from `mp3-320` to `flac`).
- **Pattern or flag changes**: re-downloads and organizes into new paths if `--pattern`, `--strip-spaces`, `--no-track-padding`, or `--replacement-text` change.
- **Removed items**: prints a warning if an album was previously synced but is no longer present in your Bandcamp collection, while preserving your local files.

Flags:
- `--pattern`: destination pattern (default: `./{artist}/{album}/{title}`).
- `--format`: audio format (`flac`, `mp3-320`, `mp3-v0`, `aac-hi`, `vorbis`, `alac`, `wav`, `aiff-lossless`). Defaults to the previous sync's format, or `mp3-320` on first run.
- `--sync-file`: path to sync state TOML file (default: `~/.config/bcextr/sync.toml`). Automatically created if it doesn't exist. Useful for syncing different formats or destinations independently (e.g. `--sync-file ./music/.sync.toml`).
- `--remove`: interactive fuzzy-find multi-select (`fzf`) over synced items to delete their files and folders from disk and mark them as skipped so they are not re-downloaded.
- `--strip-spaces`: replace spaces in metadata with `--replacement-text`.
- `--no-track-padding`: disable track number zero-padding.
- `--replacement-text`: character used to replace path-unsafe characters (default: empty).

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

### Fallback fields
Some tags (like `albumartist`) aren't always set. Use `{fieldA,fieldB}` to fall
back to `fieldB` when `fieldA` is missing, and chain as many comma-separated
fields as you want:
```sh
bcextr extract ~/Downloads/album.zip --pattern ~/Music/{albumartist,artist}/{album}/{title}
bcextr api choose --pattern ~/Music/{albumartist,artist,genre}/{album}/{title} --format flac
```
Each field is tried in order and the first one with a real value wins. If none
of them have a value, it resolves to an empty string rather than erroring.
Referencing an unknown field name anywhere in the group (a typo, for example)
still raises the usual "Param not found" error.

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
