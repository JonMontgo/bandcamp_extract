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
After installation the extractor's binary is called `bcextr`.

> **Breaking change (0.2.0):** `bcextr` is now a command group. What used to be
> `bcextr <zip>` is now `bcextr extract <zip>`.

### Extract a zip you already downloaded
```sh
bcextr extract ~/Downloads/album.zip --pattern ~/Music/{artist}/{album}/{title}
```
Default pattern if not provided is: `./{artist}/{album}/{title}`

### Pull albums straight from your Bandcamp collection
Bandcamp has no username/password API, so this reuses the same session cookie
your browser already has after you log in on bandcamp.com. A one-time login
step is required to hand that cookie to bcextr.

#### 1. Get your Bandcamp username
This is the name in the URL of your own collection page:
`https://bandcamp.com/<username>`. You can find it in the account menu on
bandcamp.com, or from the URL after clicking "Collection".

#### 2. Get your `identity` cookie
1. Log in to bandcamp.com in your browser.
2. Open developer tools (`F12`, or `Cmd+Opt+I` on macOS).
3. Go to the **Application** tab in Chrome/Edge (**Storage** tab in Firefox),
   then **Cookies** → `https://bandcamp.com` in the left sidebar.
4. Find the row named `identity` and copy its **Value** column. It's a long
   opaque string — copy the whole thing.

This cookie is a live login credential for your account: don't share it,
paste it into chat tools, or commit it anywhere. bcextr only stores it
locally in `~/.config/bcextr/session.json` (readable only by you).

#### 3. Log in with bcextr
```sh
bcextr api login
```
You'll be prompted for your Bandcamp username and the cookie value from the
steps above.

#### 4. List your collection
```sh
bcextr api list
```

#### 5. Pick albums and extract them straight to your library
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
break if Bandcamp changes it. If your cookie expires, just re-run
`bcextr api login` with a fresh value.

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
