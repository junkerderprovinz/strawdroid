# StrawKnight on Windows.
#
#   Right-click this file and choose "Run with PowerShell", or:
#   powershell -ExecutionPolicy Bypass -File start-windows.ps1
#
# WHY THIS EXISTS AND THE COMPOSE FILE IS NOT ENOUGH. The emulator needs
# /dev/kvm. On Windows the container runs inside the WSL2 virtual machine, so
# KVM has to work INSIDE a VM, which means Hyper-V has to pass the processor's
# virtualisation extensions through. That is off by default, and it is switched
# on in one file nothing prompts you to create: %USERPROFILE%\.wslconfig.
#
# Without it the container starts, the desktop serves, and the phone never
# boots. That reads as a broken image rather than as a missing setting, and the
# line that would explain it is not written anywhere. So this checks first,
# offers to write it, and only then downloads nine gigabytes.

$ErrorActionPreference = "Stop"

$Image     = "ghcr.io/junkerderprovinz/strawknight:latest"
$Container = "StrawKnight"
$Port      = 3001
$AdbPort   = 5555

function Say($t)  { Write-Host "  $t" }
function Step($t) { Write-Host "`n=== $t ===" -ForegroundColor Cyan }
function Bad($t)  { Write-Host "  $t" -ForegroundColor Red }
function Ok($t)   { Write-Host "  $t" -ForegroundColor Green }

Step "Docker"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    # Docker Desktop puts its binaries on PATH for new sessions only, so a
    # shell that was already open does not see them. Worth handling: this
    # script is most likely to be run right after the install.
    $fallback = "C:\Program Files\Docker\Docker\resources\bin"
    if (Test-Path "$fallback\docker.exe") {
        $env:PATH = "$fallback;$env:PATH"
        Say "using $fallback"
    } else {
        Bad "Docker Desktop is not installed."
        Say "Install it with:  winget install --id Docker.DockerDesktop"
        exit 1
    }
}
try { docker version --format "{{.Server.Version}}" | Out-Null }
catch { Bad "The Docker engine does not answer. Start Docker Desktop and try again."; exit 1 }
Ok "engine is up"

Step "Nested virtualisation"
# nestedVirtualization applies to the whole WSL2 machine rather than to one
# distribution, and it only takes effect after `wsl --shutdown`.
$cfg = Join-Path $env:USERPROFILE ".wslconfig"
$has = (Test-Path $cfg) -and ((Get-Content $cfg -Raw) -match "(?im)^\s*nestedVirtualization\s*=\s*true")
if ($has) {
    Ok "nestedVirtualization=true is set in $cfg"
} else {
    Bad "nestedVirtualization is missing from $cfg"
    Say "Without it the WSL machine has no /dev/kvm and the emulator will not start."
    $a = Read-Host "  Write it now and restart WSL? [y/N]"
    if ($a -notmatch "^[yYjJ]") { Say "Stopped."; exit 1 }
    if (Test-Path $cfg) { Copy-Item $cfg "$cfg.bak" -Force; Say "backup: $cfg.bak" }
    $old = if (Test-Path $cfg) { Get-Content $cfg -Raw } else { "" }
    if ($old -match "(?im)^\s*\[wsl2\]") {
        $new = $old -replace "(?im)^\s*\[wsl2\]", "[wsl2]`nnestedVirtualization=true"
    } else {
        $new = "[wsl2]`nnestedVirtualization=true`n`n$old"
    }
    Set-Content -Path $cfg -Value $new -Encoding utf8
    Ok "written"
    Say "Restarting WSL. This closes running containers."
    & wsl.exe --shutdown | Out-Null
    Start-Sleep -Seconds 8
}

Step "KVM"
# The device is checked, not the setting. A setting is a statement of intent;
# /dev/kvm is the evidence.
$kvm = (& wsl.exe -d docker-desktop -e sh -c "ls /dev/kvm >/dev/null 2>&1 && echo THERE") -join ""
if ($kvm -match "THERE") {
    Ok "/dev/kvm is there"

    # AND IT IS NOT USABLE YET. In the WSL machine the device is root:root with
    # mode 600, and the emulator inside the container runs as an ordinary user.
    # The container therefore starts, the desktop serves, and the emulator
    # prints a page about groupadd and udev rules that describes a Linux host
    # and does not apply here. Widening the mode is the whole fix.
    #
    # It has to be done on every run: the WSL machine recreates the node when
    # it restarts, and it restarts whenever Windows sleeps long enough or
    # `wsl --shutdown` is called.
    & wsl.exe -d docker-desktop -e sh -c "chmod 666 /dev/kvm" | Out-Null
    $mode = (& wsl.exe -d docker-desktop -e sh -c "ls -l /dev/kvm") -join ""
    if ($mode -match "crw-rw-rw-") { Ok "readable and writable for the container" }
    else { Bad "could not widen /dev/kvm, the emulator will probably not start"; Say $mode }
} else {
    Bad "/dev/kvm is missing inside the WSL machine."
    Say "The usual causes: virtualisation is off in the BIOS, or Windows is itself"
    Say "running in a VM that does not pass VT-x through. Without KVM the emulator"
    Say "will not start."
    exit 1
}

Step "Image"
Say "About 9 GB the first time."
docker pull $Image

Step "Start"
docker rm -f $Container 2>$null | Out-Null
docker run -d --name $Container `
    --device=/dev/kvm `
    -p "${Port}:3001" -p "${AdbPort}:5555" `
    -v strawknight-config:/config `
    --shm-size=2gb --cpus="4" --memory="8g" `
    -e TZ=(Get-TimeZone).Id `
    -e EMULATOR_GPU=swiftshader_indirect `
    -e EMULATOR_DEVICE=pixel_6 `
    -e EMULATOR_RAM=2048 `
    $Image | Out-Null

Ok "started"
Say ""
Say "Screen:  https://localhost:$Port/    (self-signed, accept it once)"
Say "Deploy:  adb connect localhost:$AdbPort"
Say ""
Say "The first start creates the device and takes a few minutes."
Say "Follow it with:  docker logs -f $Container"
Say "Stop it with:    docker stop $Container"
