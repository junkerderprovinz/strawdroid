"""The download buttons the README shows, read by gen_download_buttons.py.

Each entry names a button the generator knows and where it leads. The rows,
their order, the colours and the words are the generator's, the same in every
repository.
"""

REPO = "strawknight"
RELEASE = "https://github.com/junkerderprovinz/strawknight/releases/latest/download/"

BUTTONS = {
    "windows-script": RELEASE + "start-windows.ps1",
    "linux-script": RELEASE + "start-linux.sh",
    "compose": RELEASE + "docker-compose.yml",
    "source": "https://github.com/junkerderprovinz/strawknight/archive/refs/heads/main.zip",
}
