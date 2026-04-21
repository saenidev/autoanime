from __future__ import annotations

import httpx


class QBittorrentError(Exception):
    pass


class QBittorrentClient:
    def __init__(self, host: str, port: int, username: str, password: str):
        self.base_url = f"http://{host}:{port}"
        self.client = httpx.Client(base_url=self.base_url, timeout=10)
        self.username = username
        self.password = password
        self._logged_in = False

    def login(self) -> None:
        try:
            resp = self.client.post(
                "/api/v2/auth/login",
                data={"username": self.username, "password": self.password},
            )
        except httpx.ConnectError:
            raise QBittorrentError(
                f"qBittorrent Web UI not reachable at {self.base_url}. "
                "Is it running with Web UI enabled?"
            )

        if resp.text.strip() == "Fails.":
            raise QBittorrentError(
                "qBittorrent login failed. Check username/password in config.toml"
            )
        self._logged_in = True

    def _ensure_logged_in(self) -> None:
        if not self._logged_in:
            self.login()

    def health_check(self) -> bool:
        try:
            resp = self.client.get("/api/v2/app/version")
            return resp.status_code in (200, 403)
        except httpx.ConnectError:
            return False

    def add_torrent(
        self,
        magnet: str,
        save_path: str | None = None,
        paused: bool = False,
        tags: str | None = None,
        first_last_piece_prio: bool = True,
    ) -> bool:
        self._ensure_logged_in()
        data: dict[str, str] = {"urls": magnet}
        if save_path:
            data["savepath"] = save_path
        if paused:
            data["stopped"] = "true"
            data["paused"] = "true"
        if tags:
            data["tags"] = tags
        if first_last_piece_prio:
            data["firstLastPiecePrio"] = "true"
        try:
            resp = self.client.post("/api/v2/torrents/add", data=data)
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    def set_top_priority(self, hashes: list[str]) -> bool:
        """Move torrents to the top of the qBittorrent queue in the given order.

        Only has bandwidth impact if qBittorrent's queueing system is enabled
        (Preferences → BitTorrent → "Torrent queueing"). With queueing off
        this is cosmetic (affects UI sort order only).
        """
        self._ensure_logged_in()
        if not hashes:
            return True
        try:
            resp = self.client.post(
                "/api/v2/torrents/topPrio",
                data={"hashes": "|".join(hashes)},
            )
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    def start_torrents(self, hashes: list[str]) -> bool:
        """Resume/start paused torrents. qBittorrent v5 uses 'start', v4 uses 'resume'."""
        self._ensure_logged_in()
        if not hashes:
            return True
        payload = {"hashes": "|".join(hashes)}
        for endpoint in ("/api/v2/torrents/start", "/api/v2/torrents/resume"):
            try:
                resp = self.client.post(endpoint, data=payload)
                if resp.status_code == 200:
                    return True
            except httpx.HTTPError:
                continue
        return False

    def torrents_info(self, tag: str | None = None) -> list[dict]:
        """List torrents, optionally filtered by tag."""
        self._ensure_logged_in()
        params: dict[str, str] = {}
        if tag:
            params["tag"] = tag
        try:
            resp = self.client.get("/api/v2/torrents/info", params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError:
            return []

    def get_torrent_hashes(self) -> set[str]:
        try:
            return {t["hash"].lower() for t in self.torrents_info()}
        except KeyError:
            return set()

    def close(self) -> None:
        self.client.close()
