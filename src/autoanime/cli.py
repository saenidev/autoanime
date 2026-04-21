from __future__ import annotations

import sys
from datetime import datetime, timezone

import click

from autoanime.anilist import get_air_day, search_anime
from autoanime.config import CONFIG_PATH, generate_default_config, load_config
from autoanime.download_plan import plan_downloads
from autoanime.nyaa import fetch_rss, rank_entries
from autoanime.qbittorrent import QBittorrentClient, QBittorrentError
from autoanime.state import Show, load_state, make_slug, save_state


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """autoanime — auto-download anime from Nyaa via qBittorrent."""
    if ctx.invoked_subcommand is None:
        if not CONFIG_PATH.exists():
            path = generate_default_config()
            click.echo(f"Generated default config at {path}")
            click.echo(
                "Edit it with your qBittorrent settings, then run: "
                'autoanime add "<title>"'
            )
        else:
            click.echo(ctx.get_help())


@main.command()
@click.argument("title")
@click.option("--group", default=None, help="Override release group for this show")
@click.option("--quality", default=None, help="Override quality (e.g., 720p, 1080p)")
@click.option(
    "--dir", "download_dir", default=None, help="Download directory for this show"
)
@click.option(
    "--from",
    "from_ep",
    type=int,
    default=None,
    help="Start from episode N (marks 1..N-1 as downloaded)",
)
def add(
    title: str,
    group: str | None,
    quality: str | None,
    download_dir: str | None,
    from_ep: int | None,
) -> None:
    """Add an anime to your watchlist."""
    click.echo(f'Searching AniList for "{title}"...')
    try:
        results = search_anime(title)
    except Exception as e:
        click.echo(f"AniList search failed: {e}", err=True)
        sys.exit(1)

    if not results:
        click.echo(f'No results found on AniList for "{title}"')
        return

    top = results[0]
    click.echo(f"\nTop match:")
    click.echo(f"  Title:    {top.title_romaji}")
    if top.title_english and top.title_english != top.title_romaji:
        click.echo(f"  English:  {top.title_english}")
    click.echo(f"  Episodes: {top.episodes or '??'}")
    click.echo(f"  Status:   {top.status}")

    air_day = get_air_day(top.next_airing_at)
    if air_day:
        click.echo(f"  Air day:  {air_day}")

    if not click.confirm("\nIs this right?", default=True):
        if len(results) > 1:
            click.echo("\nOther matches:")
            for i, r in enumerate(results[1:], 2):
                click.echo(
                    f"  {i}. {r.title_romaji} ({r.episodes or '??'} eps, {r.status})"
                )
            choice = click.prompt(
                "Pick a number (or 0 to cancel)", type=int, default=0
            )
            if choice < 2 or choice > len(results):
                click.echo("Cancelled.")
                return
            top = results[choice - 1]
            air_day = get_air_day(top.next_airing_at)
        else:
            click.echo("Cancelled.")
            return

    try:
        config = load_config()
    except FileNotFoundError:
        click.echo("No config found. Run `autoanime` first to generate defaults.")
        sys.exit(1)

    shows = load_state()
    slug = make_slug(top.title_romaji)

    if slug in shows:
        click.echo(f"Already tracking {top.title_romaji}")
        return

    alt_titles: list[str] = []
    if top.title_english:
        alt_titles.append(top.title_english)
    if top.title_native:
        alt_titles.append(top.title_native)
    alt_titles.extend(top.synonyms)

    preferred_group = group or config.defaults.group_priority[0]
    preferred_quality = quality or config.defaults.quality
    search_name = top.title_romaji.split(":")[0].strip()
    search_query = f"{preferred_group} {search_name} {preferred_quality}"

    downloaded: set[int] = set()
    if from_ep and from_ep > 1:
        downloaded = set(range(1, from_ep))

    show = Show(
        anilist_id=top.id,
        title=top.title_romaji,
        alt_titles=alt_titles,
        search_query=search_query,
        group_override=group,
        quality_override=quality,
        download_dir=download_dir,
        total_episodes=top.episodes,
        airing_status=top.status,
        air_day=air_day,
        downloaded_episodes=downloaded,
    )

    shows[slug] = show
    save_state(shows)

    click.echo(f"\n✓ Now tracking {top.title_romaji}")
    if downloaded:
        click.echo(f"  Episodes 1-{from_ep - 1} marked as downloaded")
    click.echo(f"  Search query: {search_query}")


@main.command()
@click.argument("title")
def remove(title: str) -> None:
    """Remove an anime from your watchlist."""
    if not title.strip():
        click.echo("Please provide a show name to remove.")
        return
    shows = load_state()
    needle = title.lower()
    matches = [
        (slug, show)
        for slug, show in shows.items()
        if needle in show.title.lower() or needle in slug
    ]

    if not matches:
        click.echo(f'No tracked show matching "{title}"')
        return

    if len(matches) == 1:
        slug, show = matches[0]
        if click.confirm(f"Remove {show.title}?", default=True):
            del shows[slug]
            save_state(shows)
            click.echo(f"✓ Removed {show.title}")
    else:
        click.echo("Multiple matches:")
        for i, (slug, show) in enumerate(matches, 1):
            click.echo(f"  {i}. {show.title}")
        choice = click.prompt("Pick a number (or 0 to cancel)", type=int, default=0)
        if 1 <= choice <= len(matches):
            slug, show = matches[choice - 1]
            del shows[slug]
            save_state(shows)
            click.echo(f"✓ Removed {show.title}")


@main.command(name="list")
def list_shows() -> None:
    """Show tracked anime."""
    shows = load_state()
    if not shows:
        click.echo('No shows tracked. Add one with: autoanime add "<title>"')
        return

    header = f"{'Show':<35} {'Episodes':<12} {'Status':<12} {'Air Day':<10} {'Group':<15}"
    click.echo(header)
    click.echo("─" * len(header))
    for _slug, show in shows.items():
        if show.archived:
            continue
        ep_count = len(show.downloaded_episodes)
        total = str(show.total_episodes) if show.total_episodes else "??"
        ep_str = f"{ep_count}/{total}"
        group = show.group_override or "default"
        air_day = (show.air_day or "—")[:3]
        click.echo(
            f"{show.title[:34]:<35} {ep_str:<12} "
            f"{show.airing_status[:11]:<12} {air_day:<10} {group:<15}"
        )


@main.command()
@click.argument("title")
def search(title: str) -> None:
    """Search AniList without adding."""
    click.echo(f'Searching AniList for "{title}"...')
    try:
        results = search_anime(title)
    except Exception as e:
        click.echo(f"AniList search failed: {e}", err=True)
        sys.exit(1)

    if not results:
        click.echo(f'No results for "{title}"')
        return

    for i, r in enumerate(results, 1):
        air_day = get_air_day(r.next_airing_at)
        click.echo(f"\n{i}. {r.title_romaji}")
        if r.title_english and r.title_english != r.title_romaji:
            click.echo(f"   English:  {r.title_english}")
        click.echo(f"   Episodes: {r.episodes or '??'}")
        click.echo(f"   Status:   {r.status}")
        if air_day:
            click.echo(f"   Air day:  {air_day}")


@main.command()
def status() -> None:
    """Check what's available on Nyaa for tracked shows."""
    try:
        config = load_config()
    except FileNotFoundError as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    shows = load_state()
    if not shows:
        click.echo("No shows tracked.")
        return

    for _slug, show in shows.items():
        if show.archived:
            continue

        entries = fetch_rss(
            show.search_query,
            config.nyaa.mirrors,
            config.nyaa.category,
            config.nyaa.filter,
        )

        ranked = rank_entries(
            entries,
            config.defaults.group_priority,
            show.quality_override or config.defaults.quality,
            config.defaults.max_torrent_size_mb,
        )

        seen: set[int] = set()
        new_eps: list[dict] = []
        for e in ranked:
            ep = e["episode"]
            if ep not in show.downloaded_episodes and ep not in seen:
                seen.add(ep)
                new_eps.append(e)

        if new_eps:
            ep_list = ", ".join(
                str(e["episode"]) for e in sorted(new_eps, key=lambda x: x["episode"])
            )
            click.echo(
                f"{show.title} — {len(new_eps)} new episode(s) available ({ep_list})"
            )
        else:
            click.echo(f"{show.title} — up to date")


@main.command()
@click.option(
    "--dry-run", is_flag=True, help="Show what would be downloaded without downloading"
)
@click.option("--verbose", is_flag=True, help="Print detailed matching info")
def check(dry_run: bool, verbose: bool) -> None:
    """Poll Nyaa and download new episodes via qBittorrent."""
    try:
        config = load_config()
    except FileNotFoundError as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    shows = load_state()
    if not shows:
        if verbose:
            click.echo("No shows tracked.")
        return

    qbt: QBittorrentClient | None = None
    existing_hashes: set[str] = set()

    if not dry_run:
        qbt = QBittorrentClient(
            config.qbittorrent.host,
            config.qbittorrent.port,
            config.qbittorrent.username,
            config.qbittorrent.password,
        )
        if not qbt.health_check():
            click.echo(
                f"qBittorrent Web UI not reachable at "
                f"{config.qbittorrent.host}:{config.qbittorrent.port}. "
                f"Is it running with Web UI enabled?",
                err=True,
            )
            sys.exit(1)

        try:
            qbt.login()
            existing_hashes = qbt.get_torrent_hashes()
        except QBittorrentError as e:
            click.echo(str(e), err=True)
            sys.exit(1)

    downloaded: list[str] = []
    now = datetime.now(timezone.utc)

    for slug, show in shows.items():
        if show.archived:
            continue

        if verbose:
            click.echo(f"\nChecking {show.title}...")
            click.echo(f"  Query: {show.search_query}")

        entries = fetch_rss(
            show.search_query,
            config.nyaa.mirrors,
            config.nyaa.category,
            config.nyaa.filter,
        )

        if verbose:
            click.echo(f"  Found {len(entries)} RSS entries")

        ranked = rank_entries(
            entries,
            config.defaults.group_priority,
            show.quality_override or config.defaults.quality,
            config.defaults.max_torrent_size_mb,
        )

        best_per_episode: dict[int, dict] = {}
        for entry in ranked:
            ep = entry["episode"]
            if ep is None:
                continue
            if ep in show.downloaded_episodes:
                if verbose:
                    click.echo(f"  Skip ep {ep} (already downloaded)")
                continue
            if entry["info_hash"].lower() in existing_hashes:
                if verbose:
                    click.echo(f"  Skip ep {ep} (already in qBittorrent)")
                continue
            if ep not in best_per_episode:
                best_per_episode[ep] = entry

        show_tag = f"autoanime-{slug}"
        existing_show_torrents = (
            qbt.torrents_info(tag=show_tag) if qbt else []
        )
        plan = plan_downloads(
            new_episodes=list(best_per_episode.values()),
            existing_torrents=existing_show_torrents,
            max_concurrent=config.defaults.max_concurrent_per_show,
        )

        if plan.to_resume_hashes and not dry_run:
            if verbose:
                click.echo(
                    f"  Resuming {len(plan.to_resume_hashes)} paused torrent(s) for this show"
                )
            qbt.start_torrents(plan.to_resume_hashes)

        active_hashes_added: list[str] = []

        def _record(entry: dict, paused: bool) -> None:
            ep = entry["episode"]
            show.downloaded_episodes.add(ep)
            if not show.nyaa_fingerprint:
                show.nyaa_fingerprint = entry["title"]
            downloaded.append(f"{show.title} {ep}" + (" (queued)" if paused else ""))
            if verbose or dry_run:
                prefix = "[DRY RUN] Would " if dry_run else "  "
                action = "queue" if paused else "download"
                click.echo(f"{prefix}{action}: {entry['title']}")

        # Add active torrents in ascending episode order
        for entry in plan.to_add_active:
            if dry_run:
                _record(entry, paused=False)
                continue
            success = qbt.add_torrent(
                entry["magnet"],
                save_path=show.download_dir,
                paused=False,
                tags=f"autoanime,{show_tag}",
            )
            if success:
                _record(entry, paused=False)
                if entry.get("info_hash"):
                    active_hashes_added.append(entry["info_hash"].lower())
            elif verbose:
                click.echo(f"  Failed to add torrent for ep {entry['episode']}")

        # Queue-priority signal: lowest new episode number at top.
        # Effect on bandwidth requires queueing enabled in qBittorrent preferences.
        if active_hashes_added and not dry_run:
            qbt.set_top_priority(active_hashes_added)

        for entry in plan.to_add_paused:
            if dry_run:
                _record(entry, paused=True)
                continue
            success = qbt.add_torrent(
                entry["magnet"],
                save_path=show.download_dir,
                paused=True,
                tags=f"autoanime,{show_tag}",
            )
            if success:
                _record(entry, paused=True)
            elif verbose:
                click.echo(f"  Failed to queue torrent for ep {entry['episode']}")

        if (
            show.total_episodes
            and len(show.downloaded_episodes) >= show.total_episodes
            and show.airing_status == "FINISHED"
        ):
            show.archived = True
            if verbose:
                click.echo(f"  Archived {show.title} (all episodes downloaded)")

    save_state(shows)

    if qbt:
        qbt.close()

    if downloaded:
        prefix = "[DRY RUN] " if dry_run else ""
        click.echo(
            f"\n{prefix}✓ {len(downloaded)} new episode(s) "
            f"({', '.join(downloaded)})"
        )
    else:
        click.echo("\n· nothing new")


@main.group()
def schedule() -> None:
    """Manage launchd scheduling."""


@schedule.command()
def install() -> None:
    """Install launchd plist to run autoanime check on the configured interval."""
    from autoanime.scheduler import _interval_from_config, install as do_install

    try:
        path = do_install()
        secs = _interval_from_config()
        mins = secs // 60
        unit = "minute" if mins == 1 else "minutes"
        click.echo(f"✓ Installed launchd plist at {path}")
        click.echo(f"  autoanime check will run every {mins} {unit}")
    except FileNotFoundError as e:
        click.echo(str(e), err=True)
        sys.exit(1)


@schedule.command()
def uninstall() -> None:
    """Remove launchd plist."""
    from autoanime.scheduler import uninstall as do_uninstall

    do_uninstall()
    click.echo("✓ Removed launchd plist")
