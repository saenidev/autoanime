"""Tests for the qBittorrent client. HTTP layer is mocked at the httpx.Client level."""

from unittest.mock import MagicMock, patch

import pytest

from autoanime.qbittorrent import QBittorrentClient, QBittorrentError


@pytest.fixture
def client():
    c = QBittorrentClient("localhost", 8080, "admin", "adminadmin")
    c._logged_in = True
    return c


class TestAddTorrent:
    def test_returns_true_on_ok_body(self, client):
        resp = MagicMock(status_code=200, text="Ok.")
        with patch.object(client.client, "post", return_value=resp):
            assert client.add_torrent("magnet:?xt=urn:btih:abc") is True

    def test_returns_false_on_fails_body(self, client):
        """Regression: qBittorrent returns 200 with body 'Fails.' for rejected
        magnets (duplicates, parse errors). Must not be reported as success."""
        resp = MagicMock(status_code=200, text="Fails.")
        with patch.object(client.client, "post", return_value=resp):
            assert client.add_torrent("magnet:?xt=urn:btih:abc") is False

    def test_returns_false_on_non_200(self, client):
        resp = MagicMock(status_code=500, text="Server Error")
        with patch.object(client.client, "post", return_value=resp):
            assert client.add_torrent("magnet:?xt=urn:btih:abc") is False

    def test_returns_false_on_unexpected_body(self, client):
        """Defensive: if the body isn't a known success marker, treat as failure
        (could be HTML from a misconfigured proxy or unexpected qBT version)."""
        resp = MagicMock(status_code=200, text="<html>error</html>")
        with patch.object(client.client, "post", return_value=resp):
            assert client.add_torrent("magnet:?xt=urn:btih:abc") is False


class TestLogin:
    def test_success_sets_flag(self, client):
        client._logged_in = False
        resp = MagicMock(text="Ok.")
        with patch.object(client.client, "post", return_value=resp):
            client.login()
        assert client._logged_in is True

    def test_fails_body_raises(self, client):
        client._logged_in = False
        resp = MagicMock(text="Fails.")
        with patch.object(client.client, "post", return_value=resp):
            with pytest.raises(QBittorrentError, match="login failed"):
                client.login()
