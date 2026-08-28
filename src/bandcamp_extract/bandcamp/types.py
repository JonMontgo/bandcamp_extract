"""Pydantic models modeling Bandcamp's undocumented JSON/page-data shapes.

Field shapes were reverse-engineered by hitting the live endpoints with a
real session and inspecting the responses (see scripts/probe_bandcamp_api.py).
These are Bandcamp-internal, undocumented structures that can change without
notice; treat them as best-effort autocomplete aids, not a stable contract.

All models use `extra="ignore"` so Bandcamp's many unmodeled keys don't break
parsing. Date strings arrive as `"%d %b %Y %H:%M:%S GMT"` (e.g.
`"06 Aug 2026 04:01:26 GMT"`); the `BandcampDate` annotation parses them into
UTC-aware `datetime` objects at the wire boundary.

Every field carries a `description=` (visible via `model_json_schema()`) that
documents its observed purpose in the Bandcamp API. Single-letter type codes
recur throughout: ``a`` = album, ``t`` = track, ``p`` = merch/product,
``s`` = subscription (on ``sale_item_type``) or successful state (on
``state``/``sale_item_state``).
"""

from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

DownloadFormat = Literal[
    "mp3-320",
    "mp3-v0",
    "flac",
    "aac-hi",
    "vorbis",
    "alac",
    "wav",
    "aiff-lossless",
]

BANDCAMP_DATE_FORMAT = "%d %b %Y %H:%M:%S GMT"


def parse_bandcamp_date(v: Any) -> Any:
    """Parse Bandcamp's `"06 Aug 2026 04:01:26 GMT"` form into a UTC datetime.

    `None` and already-parsed datetimes pass through unchanged so the
    `BeforeValidator` is safe on optional fields.
    """
    if v is None or isinstance(v, datetime):
        return v
    return datetime.strptime(v, BANDCAMP_DATE_FORMAT).replace(tzinfo=UTC)


# Drop-in datetime type: raw string -> tz-aware UTC datetime at parse time.
BandcampDate = Annotated[datetime, BeforeValidator(parse_bandcamp_date)]


class BandcampModel(BaseModel):
    """Base for all Bandcamp wire models: tolerate unmodeled keys.

    Public so callers can do ``isinstance(obj, BandcampModel)`` /
    ``issubclass(cls, BandcampModel)`` checks against the whole family.
    """

    model_config = ConfigDict(extra="ignore", use_attribute_docstrings=True)


class ItemArt(BandcampModel):
    """Cover-art URLs for a collected/downloadable item."""

    url: str | None = Field(default=None)
    "Full-size cover-art URL (null on some items)."
    thumb_url: str | None = Field(default=None)
    "Thumbnail cover-art URL (null on some items)."
    art_id: int | None = Field(default=None)
    "Numeric id of the cover-art image (null on some items)."


class UrlHints(BandcampModel):
    """Subdomain/slug used to build a bandcamp.com item URL."""

    subdomain: str | None = Field(default=None)
    "Band's bandcamp subdomain (e.g. 'deathsdynamicshroud')."
    custom_domain: str | None = Field(default=None)
    "Custom domain if the band uses one."
    custom_domain_verified: bool | None = Field(default=None)
    "Whether the custom domain is verified."
    slug: str | None = Field(default=None)
    "Item slug used in the URL path (e.g. 'waxen-scream')."
    item_type: str | None = Field(default=None)
    """
        Single-letter item kind on url_hints: 'a' album, 't' track. Differs from
        CollectionItem.item_type which may be a full word.
    """


class CollectionItem(BandcampModel):
    """One entry from `collection_items`'s `items` list.

    Represents a single thing the fan owns (album/track/merch/gift) as returned
    by `POST /api/fancollection/1/collection_items`. Bandcamp omits/nulls out
    many fields depending on item type, so every field is optional with a
    default."""

    fan_id: int | None = Field(default=None)
    "Numeric id of the fan who owns this collection entry."
    item_id: int | None = Field(default=None)
    "Numeric id of the collected item; equals tralbum_id for albums/tracks."
    item_type: str | None = Field(default=None)
    "Kind of collected thing: 'album', 'track', or 'merch' (full word; sometimes a single letter)."
    band_id: int | None = Field(default=None)
    "Numeric id of the band/artist."
    added: BandcampDate | None = Field(default=None)
    "When the item was added to the fan's collection (Bandcamp GMT datetime)."
    updated: BandcampDate | None = Field(default=None)
    "When the collection entry was last updated (Bandcamp GMT datetime)."
    purchased: BandcampDate | None = Field(default=None)
    "When the item was purchased (Bandcamp GMT datetime; often equals `added`)."
    sale_item_id: int | None = Field(default=None)
    "Id of the sale/purchase record; pairs with sale_item_type as the key into redownload_urls."
    sale_item_type: str | None = Field(default=None)
    "Single-letter sale kind: 'a' album, 't' track, 'p' merch/product, 's' subscription."
    tralbum_id: int | None = Field(default=None)
    "Numeric id of the underlying track-or-album."
    tralbum_type: str | None = Field(default=None)
    "Single-letter tralbum discriminator: 'a' album, 't' track."
    featured_track: int | None = Field(default=None)
    "Numeric id of the preview/featured track used for hover playback."
    why: str | None = Field(default=None)
    "Free-text reason/source for the collection entry (usually null)."
    hidden: int | None = Field(default=None)
    "1 if the item is hidden from the fan's public collection."
    index: int | None = Field(default=None)
    "Positional index within the collection (usually null)."
    also_collected_count: int | None = Field(default=None)
    "How many other fans also collected this item."
    url_hints: UrlHints | None = Field(default=None)
    "Subdomain/slug used to build the item's bandcamp URL."
    item_title: str | None = Field(default=None)
    "Title of the album/track/merch."
    item_url: str | None = Field(default=None)
    "Full bandcamp.com URL of the item."
    item_art_id: int | None = Field(default=None)
    "Numeric id of the cover-art image."
    item_art_url: str | None = Field(default=None)
    "Direct URL to the full-size cover-art image."
    item_art: ItemArt | None = Field(default=None)
    "Cover-art URLs (full + thumb) and art id."
    band_name: str | None = Field(default=None)
    "Display name of the artist/band."
    band_url: str | None = Field(default=None)
    "The band's bandcamp URL."
    genre_id: int | None = Field(default=None)
    "Numeric genre id."
    featured_track_title: str | None = Field(default=None)
    "Title of the featured/preview track."
    featured_track_number: int | None = Field(default=None)
    "Track number of the featured track."
    featured_track_is_custom: bool | None = Field(default=None)
    "Whether the featured track is a custom upload."
    featured_track_duration: float | None = Field(default=None)
    "Length of the featured track in seconds."
    featured_track_url: str | None = Field(default=None)
    "Stream URL for the featured track (usually null on collection entries)."
    featured_track_encodings_id: int | None = Field(default=None)
    "Encoding id for the featured track."
    package_details: Any | None = Field(default=None)
    "Merch package/shipping details (null for digital items)."
    num_streamable_tracks: int | None = Field(default=None)
    "How many tracks can be streamed."
    is_purchasable: bool | None = Field(default=None)
    "Whether the item can still be purchased."
    is_private: bool | None = Field(default=None)
    "Whether the item is private/unlisted."
    is_preorder: bool | None = Field(default=None)
    "Whether this is a preorder."
    is_giftable: bool | None = Field(default=None)
    "Whether the item can be gifted."
    is_subscriber_only: bool | None = Field(default=None)
    "Whether the item is exclusive to subscribers."
    is_subscription_item: bool | None = Field(default=None)
    "Whether the item was obtained via a subscription."
    service_name: str | None = Field(default=None)
    "Subscription service name (e.g. 'NUWRLD Mixtape Club')."
    service_url_fragment: str | None = Field(default=None)
    "URL slug of the subscription service."
    gift_sender_name: str | None = Field(default=None)
    "Name of the gift sender (if received as a gift)."
    gift_sender_note: str | None = Field(default=None)
    "Note attached to the gift."
    gift_id: int | None = Field(default=None)
    "Numeric id of the gift (if a gift)."
    gift_recipient_name: str | None = Field(default=None)
    "Name of the gift recipient (if sent as a gift)."
    album_id: int | None = Field(default=None)
    "Numeric id of the album (equals tralbum_id for albums)."
    album_title: str | None = Field(default=None)
    "Title of the album."
    listen_in_app_url: str | None = Field(default=None)
    "Deep-link URL to open the item in the Bandcamp app."
    band_location: str | None = Field(default=None)
    "Geographic location string of the band."
    band_image_id: int | None = Field(default=None)
    "Numeric id of the band's profile image."
    release_count: int | None = Field(default=None)
    "Number of releases by the band (usually null)."
    message_count: int | None = Field(default=None)
    "Number of messages/purchase notes (usually null)."
    is_set_price: bool | None = Field(default=None)
    "Whether the item has a fixed price (not name-your-price)."
    price: float | None = Field(default=None)
    "Price paid / asking price, in `currency`."
    has_digital_download: bool | None = Field(default=None)
    "Whether a digital download is available."
    merch_ids: list[int] | None = Field(default=None)
    "List of associated merch item ids."
    merch_sold_out: bool | None = Field(default=None)
    "Whether associated merch is sold out."
    currency: str | None = Field(default=None)
    "Currency code for price (e.g. 'USD')."
    label: str | None = Field(default=None)
    "Name of the label distributing the item."
    label_id: int | None = Field(default=None)
    "Numeric id of the label."
    require_email: bool | None = Field(default=None)
    "Whether an email is required to download."
    item_art_ids: list[int] | None = Field(default=None)
    "List of additional art image ids."
    releases: list[Any] | None = Field(default=None)
    "List of releases under this item (for labels/series)."
    discount: float | None = Field(default=None)
    "Discount fraction applied (usually null)."
    token: str | None = Field(default=None)
    "Pagination/collection token for this entry."
    variant_id: int | None = Field(default=None)
    "Merch variant id (for merch with options)."
    merch_snapshot: Any | None = Field(default=None)
    "Snapshot of merch details (for merch items)."
    featured_track_license_id: int | None = Field(default=None)
    "License id of the featured track."
    licensed_item: Any | None = Field(default=None)
    "Licensing details (usually null)."
    download_available: bool | None = Field(default=None)
    "Whether the item is downloadable by this fan."
    player_data: Any | None = Field(default=None)
    "Embedded player config (usually null)."
    redownload_url: str | None = Field(default=None)
    """
        Locally injected by BandcampClient.list_collection; URL to the redownload page. Not
        present on the raw Bandcamp response.
    """

    @property
    def is_track(self) -> bool:
        """True if this collection item is a standalone track rather than an album/merch."""
        return self.item_type == "track" or self.sale_item_type == "t" or self.tralbum_type == "t"

    @property
    def is_album(self) -> bool:
        """True if this collection item is a full album."""
        return self.item_type == "album" or self.sale_item_type == "a" or self.tralbum_type == "a"

    def __str__(self) -> str:
        artist = self.band_name or "Unknown Artist"
        album = self.item_title or "Unknown Album"
        return f"[{self.sale_item_type or '?'}-{self.sale_item_id or '?'}] {artist} - {album}"


class TrackListEntry(BandcampModel):
    """One track in a per-album tracklist (from `CollectionItemsResponse.tracklists`)."""

    id: int = Field(default=0)
    "Numeric track id."
    title: str = Field(default="")
    "Track title."
    artist: str = Field(default="")
    "Track artist name."
    track_number: int | None = Field(default=None)
    "1-based position in the album (null on some Bandcamp responses)."
    duration: float | None = Field(default=None)
    "Track length in seconds (null on some Bandcamp responses)."
    file: dict[str, str] = Field(default_factory=dict)
    "Map of format -> stream URL for this track."


class ItemLookupEntry(BandcampModel):
    """One entry in `CollectionItemsResponse.item_lookup` (quick owned-check)."""

    item_type: str = Field(default="")
    "Single-letter item kind."
    purchased: bool = Field(default=False)
    """
        Whether the fan has purchased this item. NOTE: this is a bool flag, NOT a date; the name
        collides with CollectionItem.purchased.
    """


class CollectionItemsResponse(BandcampModel):
    """Response body of `POST /api/fancollection/1/collection_items` (one page)."""

    items: list[CollectionItem] = Field(default_factory=list)
    "The fan's collection entries for this page."
    more_available: bool = Field(default=False)
    "Whether another page of items exists."
    tracklists: dict[str, list[TrackListEntry]] = Field(default_factory=dict)
    'Map of "{tralbum_type}{tralbum_id}" -> per-track details.'
    redownload_urls: dict[str, str] = Field(default_factory=dict)
    'Map of "{sale_item_type}{sale_item_id}" -> redownload page URL.'
    item_lookup: dict[str, ItemLookupEntry] = Field(default_factory=dict)
    'Map of "{item_id}" -> {item_type, purchased} quick-lookup.'
    last_token: str = Field(default="")
    "Cursor for the next collection_items page; pass as older_than_token."
    purchase_infos: dict[str, Any] = Field(default_factory=dict)
    "Extra purchase metadata (usually empty)."
    collectors: dict[str, Any] = Field(default_factory=dict)
    "Collector metadata (usually empty)."


class CollectionSummary(BandcampModel):
    """The `collection_summary` block returned when authenticated."""

    fan_id: int | None = Field(default=None)
    "The fan's numeric id."
    username: str | None = Field(default=None)
    "The fan's username."
    url: str | None = Field(default=None)
    "The fan's profile URL."
    tralbum_lookup: dict[str, Any] = Field(default_factory=dict)
    "Map of owned tralbum ids."
    follows: dict[str, Any] = Field(default_factory=dict)
    "Map of followed bands/fans."


class CollectionSummaryResponse(BandcampModel):
    """Response body of `GET /api/fan/2/collection_summary`."""

    fan_id: int | None = Field(default=None)
    "The fan's numeric id (present when authenticated)."
    collection_summary: CollectionSummary | None = Field(default=None)
    "The summary block (present when authenticated)."
    error: bool | None = Field(default=None)
    "True when the identity cookie is stale/unauthenticated."
    error_message: str | None = Field(default=None)
    "Human-readable auth error message."


class FanData(BandcampModel):
    """The `fan_data` block on a fan's profile page."""

    trackpipe_url: str = Field(default="")
    "Internal fan trackpipe URL."
    username: str = Field(default="")
    "Fan's username."
    name: str = Field(default="")
    "Fan's display name."
    fan_id: int = Field(default=0)
    "Numeric fan id."
    location: str | None = Field(default=None)
    "Human-readable fan location."
    raw_location: str | None = Field(default=None)
    "Raw location string."
    bio: str = Field(default="")
    "Fan's bio text."
    photo: dict[str, Any] = Field(default_factory=dict)
    "Fan profile photo info."
    website_url: str = Field(default="")
    "Fan's external website URL."
    is_own_page: bool = Field(default=False)
    "True when viewing your own profile."
    followers_count: int = Field(default=0)
    "Number of followers."
    following_bands_count: int = Field(default=0)
    "Number of bands followed."
    following_fans_count: int = Field(default=0)
    "Number of fans followed."
    following_genres_count: int = Field(default=0)
    "Number of genres followed."
    subscriptions_count: int = Field(default=0)
    "Number of active subscriptions."
    fav_genre: str = Field(default="")
    "The fan's most-listened genre."


class ProfilePageData(BandcampModel):
    """The `#pagedata` blob on a fan's bandcamp.com/<username> page.

    Bandcamp packs dozens of other keys into this blob (locale, cfg,
    wishlist_data, followers_data, ...); only the ones this client reads are
    modeled here. `fan_data` is always present, so it's kept required."""

    fan_data: FanData = Field()
    "The logged-in fan's profile data (always present)."


class DownloadInfo(BandcampModel):
    """One available format entry within a `DownloadItem.downloads` map."""

    size_mb: str | None = Field(default=None)
    "Human-readable file size (e.g. '117.9MB', '1.3GB')."
    description: str | None = Field(default=None)
    "Human-readable format label (e.g. 'MP3 V0', 'FLAC')."
    encoding_name: str | None = Field(default=None)
    "Machine format key; matches the DownloadFormat literal (e.g. 'mp3-v0')."
    url: str | None = Field(default=None)
    "The actual zip download URL (signed, time-limited)."


class DownloadItem(BandcampModel):
    """One entry from a redownload page's `download_items` list.

    `downloads`/`sale_item_type`/`sale_item_id` are always present (they're
    what this client relies on); everything else varies by item type and is
    optional."""

    downloads: dict[str, DownloadInfo] = Field()
    "Map of format key -> download info/URL for each available format."
    sale_item_type: str = Field()
    "Single-letter sale kind: 'a' album, 't' track."
    sale_item_id: int = Field()
    "Id of the sale record."
    sale_id: int | None = Field(default=None)
    "Numeric id of the sale/purchase."
    item_type: str | None = Field(default=None)
    "Single-letter item kind: 'a' album."
    item_id: int | None = Field(default=None)
    "Numeric id of the item (equals tralbum_id for albums/tracks)."
    sale_release_date: BandcampDate | None = Field(default=None)
    "Scheduled sale release date (null when same as release_date)."
    quantity: int | None = Field(default=None)
    "Number of units in this sale."
    unit_price: float | None = Field(default=None)
    "Per-unit price paid, in `currency`."
    currency: str | None = Field(default=None)
    "Currency code (e.g. 'USD')."
    sold_date: BandcampDate | None = Field(default=None)
    "When the purchase/sale was completed (Bandcamp GMT datetime)."
    download_type: str | None = Field(default=None)
    "Single-letter download kind: 'a' album, 't' track."
    download_id: int | None = Field(default=None)
    "Numeric id of the downloadable item (equals tralbum_id)."
    sale_item_state: str | None = Field(default=None)
    "State of the sale: 's' successful."
    band_id: int | None = Field(default=None)
    "Numeric id of the selling band/artist."
    band_name: str | None = Field(default=None)
    "Name of the selling band/artist."
    genre_id: int | None = Field(default=None)
    "Numeric genre id."
    band_enabled: int | None = Field(default=None)
    "1 if the band account is active."
    has_enhanced_seller: int | None = Field(default=None)
    "1 if the seller uses enhanced seller features."
    payment_id: int | None = Field(default=None)
    "Numeric id of the payment transaction."
    payment_type: str | None = Field(default=None)
    "How it was paid: 'artistsub' subscription, 'paypal', 'stripe', etc."
    buyer_type: str | None = Field(default=None)
    "Buyer kind: 'u' for user/fan."
    buyer_id: int | None = Field(default=None)
    "Numeric id of the buying fan."
    payment_email: str | None = Field(default=None)
    "Email used for the payment."
    fulfillment_days: int | None = Field(default=None)
    "Days to fulfill (merch; null for digital)."
    package_title: str | None = Field(default=None)
    "Merch package title (null for digital)."
    package_type_id: int | None = Field(default=None)
    "Numeric merch package type (null for digital)."
    options_title: str | None = Field(default=None)
    "Selected merch option label (null for digital)."
    is_live_ticket: bool | None = Field(default=None)
    "Whether this is a live-event ticket."
    live_event_id: int | None = Field(default=None)
    "Numeric id of the live event."
    live_event_title: str | None = Field(default=None)
    "Title of the live event."
    live_event_description: str | None = Field(default=None)
    "Description of the live event."
    live_event_scheduled_start_date: BandcampDate | None = Field(default=None)
    "Live event scheduled start (Bandcamp GMT datetime)."
    live_event_scheduled_end_date: BandcampDate | None = Field(default=None)
    "Live event scheduled end (Bandcamp GMT datetime)."
    live_event_end_date: BandcampDate | None = Field(default=None)
    "When the live event ended (Bandcamp GMT datetime)."
    live_event_timezone_sym_id: str | None = Field(default=None)
    "Timezone symbol id for the live event."
    service_type: str | None = Field(default=None)
    "Subscription service type (null for non-subscription)."
    shippable: bool | None = Field(default=None)
    "Whether the item is shippable merch."
    marked_shipped_date: BandcampDate | None = Field(default=None)
    "When merch was marked shipped (Bandcamp GMT datetime)."
    license_id: int | None = Field(default=None)
    "Numeric license id (for licensed tracks)."
    option_name: str | None = Field(default=None)
    "Selected merch option name."
    package_subdomain: str | None = Field(default=None)
    "Subdomain of the merch package's band."
    package_custom_domain: str | None = Field(default=None)
    "Custom domain of the merch package's band."
    package_custom_domain_verified: bool | None = Field(default=None)
    "Whether that custom domain is verified."
    package_slug_text: str | None = Field(default=None)
    "Slug of the merch package."
    package_slug_type: str | None = Field(default=None)
    "Type letter of the merch package."
    art_id: int | None = Field(default=None)
    "Numeric id of the cover art."
    package_image_id: int | None = Field(default=None)
    "Numeric id of the merch package image."
    release_date: BandcampDate | None = Field(default=None)
    "The album/track release date (00:00:00 GMT)."
    package_release_date: BandcampDate | None = Field(default=None)
    "The merch package release date (00:00:00 GMT)."
    tralbum_id: int | None = Field(default=None)
    "Numeric id of the underlying track-or-album."
    download_pref: int | None = Field(default=None)
    "Numeric preference code for the fan's default download format."
    killed: bool | None = Field(default=None)
    "Whether this download has been revoked."
    gift_sender_note: str | None = Field(default=None)
    "Note from the gift sender."
    gift_state: str | None = Field(default=None)
    "State of the gift (pending/redeemed/etc.)."
    gift_redeemed_date: BandcampDate | None = Field(default=None)
    "When the gift was redeemed (Bandcamp GMT datetime)."
    gift_recipient_email_hidden: str | None = Field(default=None)
    "Whether the recipient email is hidden."
    gift_recipient_email: str | None = Field(default=None)
    "Email of the gift recipient."
    gift_sender_name: str | None = Field(default=None)
    "Name of the gift sender."
    gift_recipient_name: str | None = Field(default=None)
    "Name of the gift recipient."
    gift_card_value: float | None = Field(default=None)
    "Value of an associated gift card."
    gift_card_art_id: int | None = Field(default=None)
    "Art id of an associated gift card."
    gift_card_currency: str | None = Field(default=None)
    "Currency of an associated gift card."
    gift_card_recipient_email: str | None = Field(default=None)
    "Recipient email of an associated gift card."
    label_mailing_list_address: str | None = Field(default=None)
    "Label's mailing-list email address."
    label_mailing_list_unsubscribe: str | None = Field(default=None)
    "Label's mailing-list unsubscribe URL."
    subscriber_only: bool | None = Field(default=None)
    "1 if this item is subscriber-only."
    tax_system: int | None = Field(default=None)
    "Numeric tax system code."
    cart_id: int | None = Field(default=None)
    "Numeric id of the cart that produced this sale."
    state: str | None = Field(default=None)
    "Sale state: 's' successful."
    selling_band_id: int | None = Field(default=None)
    "Numeric id of the band receiving payment."
    tralbum_release_date: BandcampDate | None = Field(default=None)
    "Release date of the underlying tralbum (00:00:00 GMT)."
    merch_release_date: BandcampDate | None = Field(default=None)
    "Release date of the merch (00:00:00 GMT)."
    type: str | None = Field(default=None)
    "Full-word item kind: 'album', 'track'."
    is_preorder: bool | None = Field(default=None)
    "Whether this was a preorder."
    package_type_name: str | None = Field(default=None)
    "Human-readable merch package type name."
    includes_digital: bool | None = Field(default=None)
    "Whether the merch includes a digital download."
    nodl_desc: str | None = Field(default=None)
    "'No download' description when digital download is unavailable."
    desc: str | None = Field(default=None)
    "Short human description (e.g. '25 tracks')."
    title: str | None = Field(default=None)
    "Title of the album/track/merch."
    track_count: int | None = Field(default=None)
    "Number of tracks in the album."
    desc_track_count: int | None = Field(default=None)
    "Track count as shown in the description."
    artist: str | None = Field(default=None)
    "Artist name for display."
    url_hints: UrlHints | None = Field(default=None)
    "Subdomain/slug used to build the item's URL."
    page_url: str | None = Field(default=None)
    "Full bandcamp.com URL of the item."
    gift_link: str | None = Field(default=None)
    "URL to claim/gift the item."
    thumb_title: str | None = Field(default=None)
    "Thumbnail title for display."
    payment_amt: str | None = Field(default=None)
    "Human-readable payment amount string."
    shareable: bool | None = Field(default=None)
    "Whether the download link is shareable."
    ready: bool | None = Field(default=None)
    "Whether the download is ready."
    notify_me: bool | None = Field(default=None)
    "Whether the fan opted to be notified."
    notify_me_label: bool | None = Field(default=None)
    "Whether a label opted to be notified."
    min_price: float | None = Field(default=None)
    "Minimum name-your-price amount, in `currency`."
    is_pure_free: bool | None = Field(default=None)
    "Whether the item is strictly free (no price)."
    download_type_str: str | None = Field(default=None)
    "Human-readable download kind (e.g. 'Album')."
    paid_for: bool | None = Field(default=None)
    "Whether the fan actually paid (false for free/name-your-price at 0)."
    is_name_your_price: bool | None = Field(default=None)
    "Whether the item is name-your-price."


class DownloadPageData(BandcampModel):
    """The `#pagedata` blob on a redownload page (`item.redownload_url`).

    Like ProfilePageData, Bandcamp packs many more keys into this blob than
    modeled here; only what this client reads is included. `download_items`
    is always present, so it's kept required."""

    download_items: list[DownloadItem] = Field()
    "Per-item download metadata including the `downloads` format->URL map (always present)."
