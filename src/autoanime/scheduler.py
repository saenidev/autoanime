from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

PLIST_DIR = Path.home() / "Library" / "LaunchAgents"
PLIST_NAME = "com.autoanime.check.plist"
PLIST_PATH = PLIST_DIR / PLIST_NAME

LOG_PATH = Path.home() / ".config" / "autoanime" / "autoanime.log"


def _find_autoanime_bin() -> str:
    result = shutil.which("autoanime")
    if result:
        return result
    uv_bin = Path.home() / ".local" / "bin" / "autoanime"
    if uv_bin.exists():
        return str(uv_bin)
    raise FileNotFoundError(
        "autoanime binary not found in PATH. Install with: uv tool install ."
    )


def generate_plist(bin_path: str | None = None) -> str:
    if not bin_path:
        bin_path = _find_autoanime_bin()
    return f"""\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" \
"http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.autoanime.check</string>
    <key>ProgramArguments</key>
    <array>
        <string>{bin_path}</string>
        <string>check</string>
    </array>
    <key>StartInterval</key>
    <integer>900</integer>
    <key>StandardOutPath</key>
    <string>{LOG_PATH}</string>
    <key>StandardErrorPath</key>
    <string>{LOG_PATH}</string>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>"""


def install(bin_path: str | None = None) -> Path:
    plist_content = generate_plist(bin_path)
    PLIST_DIR.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.write_text(plist_content)
    subprocess.run(
        ["launchctl", "unload", str(PLIST_PATH)],
        check=False,
        capture_output=True,
    )
    subprocess.run(["launchctl", "load", str(PLIST_PATH)], check=True)
    return PLIST_PATH


def uninstall() -> None:
    if PLIST_PATH.exists():
        subprocess.run(["launchctl", "unload", str(PLIST_PATH)], check=False)
        PLIST_PATH.unlink()
