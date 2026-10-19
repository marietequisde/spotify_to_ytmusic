import time
from typing import Literal

import spotipy

from spotify_to_ytmusic.spotify import Spotify
from spotify_to_ytmusic.ytmusic import YTMusicTransfer

Privacy = Literal["PRIVATE", "PUBLIC"]


def _validate_privacy(privacy: Privacy) -> None:
    if privacy not in ("PRIVATE", "PUBLIC", "UNLISTED"):
        raise ValueError("privacy must be 'PRIVATE', 'UNLISTED' or 'PUBLIC'")


def _create_playlist(
    playlist: dict,
    ytmusic: YTMusicTransfer,
    *,
    name: str | None,
    description: str | None,
    privacy: Privacy,
    like_songs: bool,
    use_cache: bool,
) -> str:
    video_ids = ytmusic.search_songs(playlist["tracks"], use_cached=use_cache)
    if like_songs:
        for video_id in video_ids:
            ytmusic.rate_song(video_id, "LIKE")

    return ytmusic.create_playlist(
        name or playlist["name"],
        playlist["description"] if description is None else description,
        privacy,
        video_ids,
    )


def transfer_playlist(
    spotify_playlist_url: str,
    *,
    name: str | None = None,
    description: str | None = None,
    privacy: Privacy = "PRIVATE",
    like_songs: bool = False,
    use_cache: bool = False,
) -> str:
    """Transfer a Spotify playlist and return its new YouTube Music playlist ID."""
    _validate_privacy(privacy)
    spotify = Spotify()
    ytmusic = YTMusicTransfer()
    playlist = spotify.getSpotifyPlaylist(spotify_playlist_url)
    return _create_playlist(
        playlist,
        ytmusic,
        name=name,
        description=description,
        privacy=privacy,
        like_songs=like_songs,
        use_cache=use_cache,
    )


def transfer_liked_tracks(
    *,
    name: str | None = None,
    description: str | None = None,
    privacy: Privacy = "PRIVATE",
    like_songs: bool = False,
    use_cache: bool = False,
) -> str:
    """Transfer the authenticated Spotify user's liked tracks and return the playlist ID."""
    _validate_privacy(privacy)
    spotify = Spotify()
    if not isinstance(spotify.api.auth_manager, spotipy.SpotifyOAuth):
        raise RuntimeError(
            "Spotify OAuth is not configured; run 'spotify_to_ytmusic setup' "
            "and enable OAuth first"
        )

    ytmusic = YTMusicTransfer()
    playlist = spotify.getLikedPlaylist()
    return _create_playlist(
        playlist,
        ytmusic,
        name=name,
        description=description,
        privacy=privacy,
        like_songs=like_songs,
        use_cache=use_cache,
    )


def update_playlist(
    spotify_playlist_url: str,
    youtube_playlist_name: str,
    *,
    append: bool = False,
    use_cache: bool = False,
) -> str:
    """Update a YouTube Music playlist by name and return its playlist ID."""
    spotify = Spotify()
    ytmusic = YTMusicTransfer()
    playlist = spotify.getSpotifyPlaylist(spotify_playlist_url)
    playlist_id = ytmusic.get_playlist_id(youtube_playlist_name)
    video_ids = ytmusic.search_songs(playlist["tracks"], use_cached=use_cache)

    if not append:
        ytmusic.remove_songs(playlist_id)
    time.sleep(2)
    ytmusic.add_playlist_items(playlist_id, video_ids)
    return playlist_id


def search_track(
    spotify_track_url: str,
    *,
    use_cache: bool = False,
) -> str | None:
    """Find a Spotify track on YouTube Music and return its URL, or None if unmatched."""
    spotify = Spotify()
    ytmusic = YTMusicTransfer()
    track = spotify.getSingleTrack(spotify_track_url)
    songs = [
        {
            "name": track["name"],
            "artist": track["artists"][0]["name"],
            "duration": track["duration_ms"] / 1000,
            "album": track["album"]["name"],
        }
    ]
    video_ids = ytmusic.search_songs(songs, use_cached=use_cache)

    if not video_ids:
        return None
    return f"https://music.youtube.com/watch?v={video_ids[0]}"
