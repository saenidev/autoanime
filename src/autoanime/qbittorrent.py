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

    def add_torrent(self, magnet: str, save_path: str | None = None) -> bool:
        self._ensure_logged_in()
        data: dict[str, str] = {"urls": magnet}
        if save_path:
            data["savepath"] = save_path
        try:
            resp = self.client.post("/api/v2/torrents/add", data=data)
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    def get_torrent_hashes(self) -> set[str]:
        self._ensure_logged_in()
        try:
            resp = self.client.get("/api/v2/torrents/info")
            resp.raise_for_status()
            return {t["hash"].lower() for t in resp.json()}
        except (httpx.HTTPError, KeyError):
            return set()

    def close(self) -> None:
        self.client.close()
