#!/usr/bin/env bash
# StrawDroid on Linux.
#
#   chmod +x start-linux.sh && ./start-linux.sh
#
# The compose file does the same for anyone who keeps a stack. This one needs
# no file and checks /dev/kvm before downloading anything: without it the
# desktop serves and the phone never boots, which looks like a broken image.
set -euo pipefail

IMAGE="ghcr.io/junkerderprovinz/strawdroid:latest"
NAME="StrawDroid"
PORT="${PORT:-3001}"
ADB_PORT="${ADB_PORT:-5555}"

ok()   { printf '  \033[0;32m%s\033[0m\n' "$1"; }
bad()  { printf '  \033[0;31m%s\033[0m\n' "$1"; }
say()  { printf '  %s\n' "$1"; }
step() { printf '\n\033[0;36m=== %s ===\033[0m\n' "$1"; }

step "Docker"
if ! command -v docker >/dev/null 2>&1; then
    bad "docker is not installed."
    say "https://docs.docker.com/engine/install/"
    exit 1
fi
if ! docker info >/dev/null 2>&1; then
    bad "The Docker engine does not answer."
    say "Is the service running, and are you in the docker group?"
    exit 1
fi
ok "engine is up"

step "KVM"
if [ ! -e /dev/kvm ]; then
    bad "/dev/kvm is missing."
    say "Without KVM the emulator will not start. The usual causes:"
    say "  * virtualisation is switched off in the BIOS"
    say "  * this machine is itself a VM without nested virtualisation"
    say "  * the module is not loaded:  sudo modprobe kvm_intel   (or kvm_amd)"
    exit 1
fi
if [ ! -r /dev/kvm ] || [ ! -w /dev/kvm ]; then
    bad "/dev/kvm exists but you cannot read and write it."
    say "Usually a missing group:  sudo usermod -aG kvm \"\$USER\"  then log in again."
    say "The container will start anyway, and the phone will not boot."
fi
ok "/dev/kvm is there"

step "User"
# With the wrong owner on /config the emulator cannot write into its AVD and
# reports "A snapshot operation is pending".
PUID="$(id -u)"
PGID="$(id -g)"
say "PUID=${PUID} PGID=${PGID}"

step "Image"
say "About 9 GB the first time."
docker pull "$IMAGE"

step "Start"
docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --name "$NAME" \
    --device=/dev/kvm \
    -p "${PORT}:3001" -p "${ADB_PORT}:5555" \
    -v strawdroid-config:/config \
    --shm-size=2gb --cpus="4" --memory="8g" \
    -e PUID="${PUID}" -e PGID="${PGID}" \
    -e TZ="$(cat /etc/timezone 2>/dev/null || echo UTC)" \
    -e EMULATOR_GPU=swiftshader_indirect \
    -e EMULATOR_DEVICE=pixel_6 \
    -e EMULATOR_RAM=2048 \
    "$IMAGE" >/dev/null

ok "started"
echo
say "Screen:  https://localhost:${PORT}/    (self-signed, accept it once)"
say "Deploy:  adb connect localhost:${ADB_PORT}"
echo
say "The first start creates the device and takes a few minutes."
say "Follow it with:  docker logs -f ${NAME}"
say "Stop it with:    docker stop ${NAME}"
