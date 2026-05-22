import logging
import re
import subprocess
import threading
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import yt_dlp
from django.conf import settings

logger = logging.getLogger("downloader")

ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def clean_error_msg(error) -> str:
    msg = ANSI_RE.sub("", str(error))
    msg = msg.encode("ascii", "ignore").decode("ascii")
    return msg[:700]


class YoutubeUrlHelper:
    @staticmethod
    def normalize(url: str) -> str:
        try:
            u = urlparse(url)
            host = (u.netloc or "").lower()

            if host in {"music.youtube.com", "m.music.youtube.com"}:
                qs = parse_qs(u.query)
                keep = {k: qs[k][0] for k in ("v", "list", "index") if k in qs}
                if not keep:
                    return url

                return urlunparse(
                    u._replace(
                        netloc="www.youtube.com",
                        path="/playlist" if "list" in keep else "/watch",
                        query=urlencode(keep),
                    )
                )

            return url
        except Exception:
            return url


class FormatSelector:
    MP3_BITRATES = {
        "best": "320",
        "320": "320",
        "256": "256",
        "192": "192",
        "128": "128",
    }

    @classmethod
    def mp3(cls, q):
        q = str(q or "best").lower().strip()
        return cls.MP3_BITRATES.get(q, "320")


class ProgressTracker:
    def __init__(self, download, total):
        self.download = download
        self.total = max(total, 1)
        self.done = 0
        self.lock = threading.Lock()

    def inc(self):
        with self.lock:
            self.done += 1
            pct = 12 + int((self.done / self.total) * 73)
            self.download.progress = min(pct, 85)
            self.download.save(update_fields=["progress", "updated_at"])


def _base_ydl_opts() -> dict:
    return {
        "noplaylist": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["web"],
            }
        },
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
        "windowsfilenames": True,
        "restrictfilenames": True,
        "trim_file_name": 80,
        "overwrites": True,
        "nopart": False,
        "nocheckcertificate": True,
        "retries": 10,
        "fragment_retries": 10,
        "file_access_retries": 10,
        "extractor_retries": 5,
        "concurrent_fragment_downloads": 2,
        "buffersize": 1024 * 1024,
        "socket_timeout": 30,
        "prefer_ffmpeg": True,
        "quiet": True,
        "no_warnings": False,
    }


class DownloadService:
    def __init__(self, download):
        self.download = download
        self.media_dir = Path(settings.MEDIA_ROOT) / "downloads"
        self.media_dir.mkdir(parents=True, exist_ok=True)

    def _save_metadata_once(self, info: dict):
        if self.download.title:
            return

        self.download.title = info.get("title") or "Unknown Video"
        self.download.channel_name = info.get("uploader") or "Unknown Creator"
        self.download.duration = info.get("duration") or 0
        self.download.save(
            update_fields=["title", "channel_name", "duration", "updated_at"]
        )

    def execute(self) -> bool:
        try:
            self.download.url = YoutubeUrlHelper.normalize(self.download.url)
            self.download.status = "downloading"
            self.download.progress = 5
            self.download.save(update_fields=["url", "status", "progress", "updated_at"])

            fmt = (self.download.format or "").lower().strip()

            if fmt in ("mp4", "video"):
                return self._download_mp4()

            if fmt in ("mp3", "audio", "audio_only"):
                return self._download_mp3()

            self._fail(f"Unsupported format: {self.download.format}")
            return False

        except Exception as e:
            logger.exception("Execution failed")
            self._fail(clean_error_msg(e))
            return False

    def _download_mp4(self) -> bool:
        try:
            output_base = self.media_dir / f"download_{self.download.id}"
            output_template = str(output_base) + ".%(ext)s"

            for old in self.media_dir.glob(f"download_{self.download.id}*"):
                try:
                    old.unlink()
                except Exception:
                    pass

            ydl_opts = {
                **_base_ydl_opts(),
                "format": "best",
                "outtmpl": output_template,
                "merge_output_format": "mp4",
                "progress_hooks": [self._mp4_hook],
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.download.url, download=True)

            if not info:
                self._fail("Download returned no info")
                return False

            self._save_metadata_once(info)

            mp4 = self.media_dir / f"download_{self.download.id}.mp4"
            if mp4.exists() and mp4.stat().st_size > 0:
                self._complete(str(mp4.relative_to(settings.MEDIA_ROOT)))
                return True

            possible_sources = [
                self.media_dir / f"download_{self.download.id}.webm",
                self.media_dir / f"download_{self.download.id}.mkv",
                self.media_dir / f"download_{self.download.id}.mov",
            ]

            for source_file in possible_sources:
                if source_file.exists() and source_file.stat().st_size > 0:
                    cmd = [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(source_file),
                        "-c:v",
                        "copy",
                        "-c:a",
                        "aac",
                        str(mp4),
                    ]
                    subprocess.run(cmd, check=True)

                    if mp4.exists() and mp4.stat().st_size > 0:
                        try:
                            source_file.unlink()
                        except Exception:
                            pass
                        self._complete(str(mp4.relative_to(settings.MEDIA_ROOT)))
                        return True

            existing = []
            for p in self.media_dir.glob(f"download_{self.download.id}*"):
                try:
                    existing.append(f"{p.name} ({p.stat().st_size} bytes)")
                except Exception:
                    existing.append(p.name)

            self._fail(f"MP4 not found after download. Existing files: {existing}")
            return False

        except Exception as e:
            logger.exception("MP4 error")
            self._fail(clean_error_msg(e))
            return False

    def _mp4_hook(self, d):
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            if total:
                pct = int((d.get("downloaded_bytes", 0) / total) * 60)
                self._progress(10 + pct)
        elif d.get("status") == "finished":
            self._progress(85)

    def _download_mp3(self) -> bool:
        try:
            probe_opts = {
                **_base_ydl_opts(),
                "quiet": True,
                "skip_download": True,
                "extract_flat": True,
                "noplaylist": False,
            }

            with yt_dlp.YoutubeDL(probe_opts) as ydl:
                info = ydl.extract_info(self.download.url, download=False)

            if info and isinstance(info.get("entries"), list) and len(info["entries"]) > 1:
                if not self.download.title and info.get("title"):
                    self.download.title = info["title"]
                    self.download.save(update_fields=["title", "updated_at"])
                return self._download_mp3_playlist(info)

            return self._download_mp3_single(self.download.url)

        except Exception as e:
            logger.exception("MP3 error")
            self._fail(clean_error_msg(e))
            return False

    def _download_mp3_single(self, url: str) -> bool:
        try:
            output_base = self.media_dir / f"download_{self.download.id}"
            output_template = str(output_base) + ".%(ext)s"

            for old in self.media_dir.glob(f"download_{self.download.id}*"):
                try:
                    old.unlink()
                except Exception:
                    pass

            ydl_opts = {
                **_base_ydl_opts(),
                "format": "ba/bestaudio/best",
                "outtmpl": output_template,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": FormatSelector.mp3(self.download.quality),
                    }
                ],
                "progress_hooks": [self._mp3_hook],
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

            if not info:
                self._fail("MP3 download returned no info")
                return False

            self._save_metadata_once(info)

            mp3 = self.media_dir / f"download_{self.download.id}.mp3"
            if not mp3.exists() or mp3.stat().st_size <= 0:
                existing = []
                for p in self.media_dir.glob(f"download_{self.download.id}*"):
                    try:
                        existing.append(f"{p.name} ({p.stat().st_size} bytes)")
                    except Exception:
                        existing.append(p.name)

                self._fail(f"MP3 not found after download. Existing files: {existing}")
                return False

            self._complete(str(mp3.relative_to(settings.MEDIA_ROOT)))
            return True

        except Exception as e:
            logger.exception("MP3 single error")
            self._fail(clean_error_msg(e))
            return False

    def _download_mp3_playlist(self, pl_info: dict) -> bool:
        urls = [
            YoutubeUrlHelper.normalize(e["url"])
            for e in pl_info.get("entries", [])
            if e and "url" in e
        ]

        if not urls:
            self._fail("No URLs in playlist")
            return False

        tracker = ProgressTracker(self.download, len(urls))
        work = self.media_dir / f"pl_{self.download.id}"
        work.mkdir(exist_ok=True)

        def task(u, idx):
            try:
                ydl_opts = {
                    **_base_ydl_opts(),
                    "format": "ba/bestaudio/best",
                    "outtmpl": str(work / f"{idx:03d}_%(title).80s.%(ext)s"),
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": FormatSelector.mp3(self.download.quality),
                        }
                    ],
                    "quiet": True,
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.extract_info(u, download=True)

                tracker.inc()

            except Exception as e:
                logger.warning(f"Playlist track {idx} failed: {clean_error_msg(e)}")
                tracker.inc()

        with ThreadPoolExecutor(max_workers=4) as ex:
            futures = [ex.submit(task, u, i) for i, u in enumerate(urls, 1)]
            for future in futures:
                try:
                    future.result()
                except Exception:
                    pass

        mp3s = list(work.glob("*.mp3"))
        if not mp3s:
            self._fail("All playlist tracks failed")
            return False

        safe = (
            "".join(
                c for c in (self.download.title or "playlist")
                if c.isalnum() or c in " _-"
            ).strip()
            or "playlist"
        )

        zip_path = self.media_dir / f"{safe}_{self.download.id}.zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
            for f in sorted(mp3s):
                zf.write(f, f.name)
                try:
                    f.unlink()
                except Exception:
                    pass

        try:
            work.rmdir()
        except OSError:
            pass

        self._complete(str(zip_path.relative_to(settings.MEDIA_ROOT)))
        return True

    def _mp3_hook(self, d):
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            if total:
                pct = int((d.get("downloaded_bytes", 0) / total) * 50)
                self._progress(20 + pct)
        elif d.get("status") == "finished":
            self._progress(85)

    def _progress(self, pct: int):
        self.download.progress = min(pct, 100)
        self.download.save(update_fields=["progress", "updated_at"])

    def _complete(self, path: str):
        self.download.status = "completed"
        self.download.progress = 100
        self.download.file_path = path
        self.download.error = None
        self.download.save(
            update_fields=["status", "progress", "file_path", "error", "updated_at"]
        )

    def _fail(self, msg: str):
        self.download.status = "failed"
        self.download.progress = 0
        self.download.error = clean_error_msg(msg)
        self.download.save(update_fields=["status", "progress", "error", "updated_at"])