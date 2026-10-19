from unittest.mock import Mock

import pytest

from spotify_to_ytmusic import api


@pytest.fixture
def clients(monkeypatch):
    spotify = Mock()
    ytmusic = Mock()
    monkeypatch.setattr(api, "Spotify", lambda: spotify)
    monkeypatch.setattr(api, "YTMusicTransfer", lambda: ytmusic)
    return spotify, ytmusic


def test_transfer_playlist_returns_id_and_uses_options(clients):
    spotify, ytmusic = clients
    spotify.getSpotifyPlaylist.return_value = {
        "name": "Source playlist",
        "description": "Source description",
        "tracks": [{"name": "Song"}],
    }
    ytmusic.search_songs.return_value = ["video-id"]
    ytmusic.create_playlist.return_value = "playlist-id"

    result = api.transfer_playlist(
        "spotify-url",
        name="New name",
        description="New description",
        privacy="PUBLIC",
        like_songs=True,
        use_cache=True,
    )

    assert result == "playlist-id"
    spotify.getSpotifyPlaylist.assert_called_once_with("spotify-url")
    ytmusic.search_songs.assert_called_once_with([{"name": "Song"}], use_cached=True)
    ytmusic.rate_song.assert_called_once_with("video-id", "LIKE")
    ytmusic.create_playlist.assert_called_once_with(
        "New name", "New description", "PUBLIC", ["video-id"]
    )


def test_transfer_playlist_uses_source_name_and_description(clients):
    spotify, ytmusic = clients
    spotify.getSpotifyPlaylist.return_value = {
        "name": "Source playlist",
        "description": "Source description",
        "tracks": [],
    }
    ytmusic.search_songs.return_value = []

    result = api.transfer_playlist("spotify-url")

    assert result == ytmusic.create_playlist.return_value
    spotify.getSpotifyPlaylist.assert_called_once_with("spotify-url")
    ytmusic.create_playlist.assert_called_once_with(
        "Source playlist", "Source description", "PRIVATE", []
    )


def test_transfer_playlist_rejects_unsupported_privacy(clients):
    spotify, ytmusic = clients
    spotify.getSpotifyPlaylist.return_value = {
        "name": "Playlist",
        "description": "",
        "tracks": [],
    }

    with pytest.raises(ValueError, match="privacy"):
        api.transfer_playlist("spotify-url", privacy="UNLISTED")

    spotify.getSpotifyPlaylist.assert_not_called()
    ytmusic.search_songs.assert_not_called()


def test_transfer_liked_tracks_requires_oauth(clients):
    spotify, _ = clients

    with pytest.raises(RuntimeError, match="OAuth is not configured"):
        api.transfer_liked_tracks()

    spotify.getLikedPlaylist.assert_not_called()


def test_transfer_liked_tracks_uses_oauth_account(clients, monkeypatch):
    spotify, ytmusic = clients
    oauth_type = type("FakeSpotifyOAuth", (), {})
    monkeypatch.setattr(api.spotipy, "SpotifyOAuth", oauth_type)
    spotify.api.auth_manager = oauth_type()
    spotify.getLikedPlaylist.return_value = {
        "name": "Liked songs",
        "description": "Saved tracks",
        "tracks": [],
    }
    ytmusic.search_songs.return_value = []

    result = api.transfer_liked_tracks()

    assert result == ytmusic.create_playlist.return_value
    spotify.getLikedPlaylist.assert_called_once_with()


def test_update_playlist_appends_without_removing(clients, monkeypatch):
    spotify, ytmusic = clients
    spotify.getSpotifyPlaylist.return_value = {"tracks": []}
    ytmusic.get_playlist_id.return_value = "playlist-id"
    ytmusic.search_songs.return_value = ["video-id"]
    monkeypatch.setattr(api.time, "sleep", lambda _: None)

    result = api.update_playlist("spotify-url", "playlist", append=True)

    assert result == "playlist-id"
    ytmusic.remove_songs.assert_not_called()
    ytmusic.add_playlist_items.assert_called_once_with("playlist-id", ["video-id"])


def test_update_playlist_replaces_existing_tracks(clients, monkeypatch):
    spotify, ytmusic = clients
    spotify.getSpotifyPlaylist.return_value = {"tracks": []}
    ytmusic.get_playlist_id.return_value = "playlist-id"
    ytmusic.search_songs.return_value = []
    monkeypatch.setattr(api.time, "sleep", lambda _: None)

    api.update_playlist("spotify-url", "playlist")

    ytmusic.remove_songs.assert_called_once_with("playlist-id")


def test_search_track_returns_none_without_match(clients):
    spotify, ytmusic = clients
    spotify.getSingleTrack.return_value = {
        "name": "Song",
        "artists": [{"name": "Artist"}],
        "duration_ms": 120000,
        "album": {"name": "Album"},
    }
    ytmusic.search_songs.return_value = []

    assert api.search_track("track-url") is None
    ytmusic.search_songs.assert_called_once_with(
        [{"name": "Song", "artist": "Artist", "duration": 120, "album": "Album"}],
        use_cached=False,
    )


def test_search_track_returns_youtube_url(clients):
    spotify, ytmusic = clients
    spotify.getSingleTrack.return_value = {
        "name": "Song",
        "artists": [{"name": "Artist"}],
        "duration_ms": 120000,
        "album": {"name": "Album"},
    }
    ytmusic.search_songs.return_value = ["video-id"]

    assert api.search_track("track-url") == "https://music.youtube.com/watch?v=video-id"
