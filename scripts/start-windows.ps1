# StrawDroid on Windows.
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

$Image     = "ghcr.io/junkerderprovinz/strawdroid:latest"
$Container = "StrawDroid"
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
# TWO THINGS HAVE TO HAPPEN, and neither is done for us.
#
# First, the KVM module is not loaded when the WSL machine boots, so /dev/kvm
# does not exist at all, nested virtualisation or not. modprobe registers the
# misc device and the node appears.
#
# Second, the node then belongs to root with mode 600, while the emulator
# inside the container runs as an ordinary user. Left alone, the container
# starts, the desktop serves, and the emulator prints a page about groupadd
# and udev rules that describes a Linux host and does not apply here.
#
# Both are repeated on every run on purpose: the WSL machine is rebuilt
# whenever Docker Desktop restarts, and everything done inside it is gone.
& wsl.exe -d docker-desktop -e sh -c "modprobe kvm_intel 2>/dev/null || modprobe kvm_amd 2>/dev/null; chmod 666 /dev/kvm 2>/dev/null" | Out-Null
$mode = (& wsl.exe -d docker-desktop -e sh -c "ls -l /dev/kvm 2>&1") -join ""
if ($mode -match "crw-rw-rw-") {
    Ok "/dev/kvm is there and open for the container"
} elseif ($mode -match "No such file") {
    Bad "/dev/kvm is missing inside the WSL machine."
    Say "The usual causes: virtualisation is off in the BIOS, or Windows is itself"
    Say "running in a VM that does not pass VT-x through. Without KVM the emulator"
    Say "will not start."
    exit 1
} else {
    Bad "could not open /dev/kvm for the container; the emulator will probably not start"
    Say $mode
}

Step "Image"
Say "About 9 GB the first time."
docker pull $Image

Step "Start"
docker rm -f $Container 2>$null | Out-Null
docker run -d --name $Container `
    --device=/dev/kvm `
    -p "${Port}:3001" -p "${AdbPort}:5555" `
    -v strawdroid-config:/config `
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
