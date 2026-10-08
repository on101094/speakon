import hashlib
import os
import shutil
import subprocess
import sys
import io
import zipfile
from pathlib import Path

import pytest

import updates


def release(tag="v1.2.5", data=b"zip", digest=True):
    asset = {"name": f"SpeakOn-{tag[1:]}-windows-x64.zip", "browser_download_url": "https://x/zip", "size": len(data)}
    if digest:
        asset["digest"] = "sha256:" + hashlib.sha256(data).hexdigest()
    return {"tag_name": tag, "html_url": "https://x/page", "body": "notes", "assets": [asset]}


def test_versions_compare_as_numbers():
    assert updates.parse_version("v1.2.10") > updates.parse_version("1.2.9")
    assert updates.parse_version("nightly") is None


@pytest.mark.parametrize("tag, newer", [("v1.2.5", True), ("v1.2.4", False), ("v1.1.9", False), ("junk", False)])
def test_check_reports_only_newer_releases(tag, newer):
    info = updates.check("1.2.4", fetch=lambda: release(tag))
    assert (info is not None) == newer
    if newer:
        assert info["version"] == "1.2.5" and info["zip"] == "https://x/zip" and len(info["sha256"]) == 64


def fake_download(data):
    return lambda url: io.BytesIO(data)


def test_download_checks_the_fingerprint(tmp_path):
    info = updates.check("1.2.4", fetch=lambda: release(data=b"good"))
    assert updates.download(info, tmp_path, opener=fake_download(b"good")).read_bytes() == b"good"
    with pytest.raises(RuntimeError, match="damaged"):
        updates.download(info, tmp_path, opener=fake_download(b"evil"))
    assert not list(tmp_path.glob("*.zip"))


def test_download_refuses_a_release_without_a_fingerprint(tmp_path):
    info = updates.check("1.2.4", fetch=lambda: release(digest=False))
    with pytest.raises(RuntimeError, match="verify"):
        updates.download(info, tmp_path, opener=fake_download(b"zip"))


def make_zip(path, names):
    with zipfile.ZipFile(path, "w") as z:
        for n in names:
            z.writestr(n, "x")


def test_unpack_finds_the_new_app(tmp_path):
    make_zip(tmp_path / "u.zip", ["SpeakOn\\SpeakOn.exe", "SpeakOn/_internal/a.dll"])   # Windows zips may use \
    new = updates.unpack(tmp_path / "u.zip", tmp_path / "work")
    assert (new / "SpeakOn.exe").exists() and (new / "_internal" / "a.dll").exists()


@pytest.mark.parametrize("names", [["SpeakOn/SpeakOn.exe", "../evil.txt"], ["Other/readme.txt"]])
def test_unpack_rejects_unsafe_or_wrong_zips(tmp_path, names):
    make_zip(tmp_path / "u.zip", names)
    with pytest.raises(RuntimeError):
        updates.unpack(tmp_path / "u.zip", tmp_path / "work")
    assert not (tmp_path / "evil.txt").exists()


def test_swap_script_quotes_paths_and_restarts():
    s = updates.swap_script(42, r"C:\Users\O'Neil\SpeakOn\update\new\SpeakOn", r"D:\Apps\SpeakOn",
                            r"C:\Users\O'Neil\SpeakOn\update", r"C:\log.txt")
    assert "Wait-Process -Id 42" in s and "Stop-Process -Id 42" in s
    assert r"'C:\Users\O''Neil\SpeakOn\update\new\SpeakOn'" in s
    assert r"Start-Process -FilePath 'D:\Apps\SpeakOn\SpeakOn.exe'" in s


def test_can_install_only_a_built_app_in_a_writable_folder(tmp_path):
    assert updates.can_install(tmp_path)
    assert not updates.can_install(tmp_path / "missing")
    assert updates.app_dir() is None          # tests run from source


@pytest.mark.skipif(sys.platform != "win32", reason="the swap runs PowerShell and robocopy")
def test_swap_replaces_the_files_after_the_app_closes(tmp_path):
    target, work = tmp_path / "app", tmp_path / "update"
    new = work / "new" / "SpeakOn"
    (target / "_internal").mkdir(parents=True)
    (target / "_internal" / "old.dll").write_text("old")
    (target / "_internal" / "keep.txt").write_text("mine")
    (new / "_internal").mkdir(parents=True)
    (new / "_internal" / "old.dll").write_text("new")
    shutil.copy(Path(os.environ["SystemRoot"]) / "System32" / "whoami.exe", new / "SpeakOn.exe")
    app = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(3)"])   # "SpeakOn", still closing
    script = tmp_path / "update.ps1"
    script.write_text(updates.swap_script(app.pid, new, target, work, tmp_path / "update.log"), encoding="utf-8-sig")
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
                   check=True, timeout=90)
    assert app.poll() is not None                                   # waited for it to close first
    assert (target / "_internal" / "old.dll").read_text() == "new"
    assert (target / "_internal" / "keep.txt").read_text() == "mine"
    assert (target / "SpeakOn.exe").exists() and not work.exists()


LOCK = """
import ctypes, sys, time
from ctypes import wintypes
k = ctypes.WinDLL("kernel32", use_last_error=True)
k.CreateFileW.restype = wintypes.HANDLE
# read sharing only, like an antivirus scanning the file: others may read it (the backup) but not write it
h = k.CreateFileW(sys.argv[1], 0x80000000, 1, None, 3, 0x80, None)
assert h != wintypes.HANDLE(-1).value, ctypes.get_last_error()
print("locked", flush=True)
time.sleep(float(sys.argv[2]))
"""


@pytest.mark.skipif(sys.platform != "win32", reason="the swap runs PowerShell and robocopy")
def test_a_failed_copy_puts_the_old_version_back(tmp_path):
    target, work = tmp_path / "app", tmp_path / "update"
    new = work / "new" / "SpeakOn"
    for folder, word in [(target, "old"), (new, "new")]:
        (folder / "_internal").mkdir(parents=True)
        (folder / "_internal" / "a.dll").write_text(word)
        (folder / "_internal" / "z.dll").write_text(word)
        shutil.copy(Path(os.environ["SystemRoot"]) / "System32" / "whoami.exe", folder / "SpeakOn.exe")
    locker = subprocess.Popen([sys.executable, "-c", LOCK, str(target / "_internal" / "z.dll"), "40"],
                              stdout=subprocess.PIPE, text=True)
    assert locker.stdout.readline().strip() == "locked"
    log = tmp_path / "update.log"
    script = tmp_path / "update.ps1"
    script.write_text(updates.swap_script(999999, new, target, work, log), encoding="utf-8-sig")
    try:
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
                       check=True, timeout=120)
    finally:
        locker.kill()
    assert "restoring the old version" in log.read_text(encoding="utf-8-sig", errors="replace")
    assert (target / "_internal" / "a.dll").read_text() == "old"     # put back, not left half-updated
    assert not work.exists()
