"""New versions: ask GitHub once a day, and install one on request.

Only the public releases page of this project is read (api.github.com); nothing about the user or
their dictations is sent. Installing downloads the release zip, checks it against the SHA-256 that
GitHub publishes for it, unpacks it next to this one, and leaves a small script that copies the new
files over the old ones once SpeakOn has closed, then starts the new version.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path, PureWindowsPath

import config as C

LATEST = "https://api.github.com/repos/on101094/speakon/releases/latest"
TIMEOUT = 15


def parse_version(text):
    """'v1.2.10' -> (1, 2, 10); None if it isn't a version."""
    try:
        return tuple(int(p) for p in str(text).strip().lstrip("vV").split("."))
    except ValueError:
        return None


def _get(url):
    headers = {"User-Agent": f"{C.APP_NAME}/{C.VERSION}", "Accept": "application/vnd.github+json"}
    if os.environ.get("SPEAKON_GITHUB_TOKEN") and url.startswith("https://api.github.com/"):
        headers["Authorization"] = "Bearer " + os.environ["SPEAKON_GITHUB_TOKEN"]   # CI only
    req = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(req, timeout=TIMEOUT)


def check(current=C.VERSION, fetch=None):
    """The newest release if it is newer than `current`, else None. Raises on network errors."""
    if fetch is None:
        with _get(LATEST) as r:
            release = json.load(r)
    else:
        release = fetch()
    new, now = parse_version(release.get("tag_name")), parse_version(current)
    if not new or not now or new <= now:
        return None
    asset = next((a for a in release.get("assets", []) if a.get("name", "").endswith("-windows-x64.zip")), None)
    digest = (asset or {}).get("digest") or ""
    return {"version": ".".join(map(str, new)), "page": release.get("html_url", ""),
            "notes": release.get("body", "") or "",
            "zip": asset and asset.get("browser_download_url"), "size": asset and asset.get("size"),
            "sha256": digest[7:].lower() if digest.startswith("sha256:") else None}


def app_dir():
    """The folder SpeakOn.exe runs from, or None when running from source."""
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else None


def can_install(target=None):
    """True when an update can replace the files in place (a built SpeakOn.exe in a folder we may write)."""
    target = target or app_dir()
    if target is None:
        return False
    probe = target / ".speakon-update-test"
    try:
        probe.write_text("")
        probe.unlink()
        return True
    except OSError:
        return False


def download(info, work, progress=lambda done, total: None, opener=None):
    """Download and verify the release zip into `work`; returns its path."""
    if not info.get("zip") or not info.get("sha256"):
        raise RuntimeError("this release has no download SpeakOn can verify")
    work.mkdir(parents=True, exist_ok=True)
    path = work / f"SpeakOn-{info['version']}.zip"
    h = hashlib.sha256()
    total = info.get("size") or 0
    done = 0
    with (opener or _get)(info["zip"]) as r, open(path, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
            h.update(chunk)
            done += len(chunk)
            progress(done, total)
    if h.hexdigest() != info["sha256"]:
        path.unlink(missing_ok=True)
        raise RuntimeError("the download is damaged (its fingerprint does not match) - nothing was changed")
    return path


def unpack(zip_path, work):
    """Unpack the release zip; returns the folder holding the new SpeakOn.exe."""
    out = work / "new"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    root = out.resolve()
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            name = info.filename.replace("\\", "/")
            dest = (out / name).resolve()
            if dest != root and root not in dest.parents:
                raise RuntimeError(f"unsafe path in the update: {info.filename}")
            if name.endswith("/"):
                dest.mkdir(parents=True, exist_ok=True)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(dest, "wb") as dst:
                shutil.copyfileobj(src, dst)
    new = out / C.APP_NAME
    if not (new / f"{C.APP_NAME}.exe").exists():
        raise RuntimeError("the update does not contain SpeakOn.exe")
    return new


def _q(path):
    return "'" + str(path).replace("'", "''") + "'"


def swap_script(pid, new, target, work, log):
    """PowerShell that waits for this SpeakOn to close, copies the new files over it and starts it again."""
    exe = PureWindowsPath(target) / f"{C.APP_NAME}.exe"
    return "\n".join([
        f"Wait-Process -Id {int(pid)} -Timeout 60 -ErrorAction SilentlyContinue",
        f"Stop-Process -Id {int(pid)} -Force -ErrorAction SilentlyContinue",   # stuck closing: its files must be free
        f"robocopy {_q(new)} {_q(target)} /E /R:10 /W:1 /NP /NJH /NFL /NDL | Out-File -Append -Encoding utf8 {_q(log)}",
        f"if ($LASTEXITCODE -ge 8) {{ \"update copy failed: $LASTEXITCODE\" | Out-File -Append -Encoding utf8 {_q(log)} }}",
        f"Start-Process -FilePath {_q(exe)}",
        f"Remove-Item -Recurse -Force {_q(work)} -ErrorAction SilentlyContinue",
        "",
    ])


def start_swap(new, target, work=None, launch=None):
    """Leave the swap script running; the caller then quits SpeakOn."""
    work = work or (C.DATA_DIR / "update")
    script = C.DATA_DIR / "update.ps1"
    log = C.DATA_DIR / "logs" / "update.log"
    script.write_text(swap_script(os.getpid(), new, target, work, log), encoding="utf-8-sig")
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", str(script)]
    if launch:
        return launch(cmd)
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    return subprocess.Popen(cmd, creationflags=flags, close_fds=True)
