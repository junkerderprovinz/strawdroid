# syntax=docker/dockerfile:1.26
#
# StrawKnight - an Android phone you can hit as hard as you like
# -----------------------------------------------------------------------------
# A straw knight is the practice dummy: built in the shape of the real thing so
# somebody can strike at it without anybody getting hurt. That is what this is.
# It runs the REAL Android emulator - the same AVD Android Studio starts - with
# its screen on a Selkies desktop, so an app under development can be installed,
# driven and broken without an APK ever touching a phone.
#
# WHY NOT Android-in-a-container (ReDroid, Waydroid). Those run the Android
# userspace directly on the host kernel: no battery, no motion sensor, no power
# HAL. Doze therefore never fires, WorkManager runs more eagerly than it ever
# would on real hardware, and Android 14's limits on a dataSync foreground
# service never kick in. For an app whose whole job is syncing files in the
# background, a rig that is green because it never asks the question is worse
# than no rig at all. A real AVD answers, and `dumpsys deviceidle force-idle`
# makes it answer on demand.
#
# WHY NOT budtmo/docker-android, which does the same job and is well kept. Its
# screen is x11vnc plus noVNC: a framebuffer diff over websockets, no hardware
# encoding. Judging how an app FEELS is judging its scrolling and its
# transitions, which is exactly what noVNC smears. This one puts the emulator on
# the same Selkies/WebRTC desktop as the rest of the house, hardware-encoded on
# the box's own GPU.
#
# House pattern copied from junkerderprovinz/krusader and the Crucible sandbox:
# LinuxServer Selkies base, s6-overlay init, HTTPS WebUI on 3001, no login by
# default. GPU wiring is supplied at `docker run` via the Unraid template rather
# than baked in, which keeps the image vendor-neutral.
#
# Flavour PINNED on purpose, never :latest and never the floating :dev tag.
ARG BASE_TAG=ubunturesolute
FROM ghcr.io/linuxserver/baseimage-selkies:${BASE_TAG}

LABEL maintainer="junkerderprovinz"
LABEL org.opencontainers.image.title="strawknight"
LABEL org.opencontainers.image.description="StrawKnight - a real Android emulator on a Selkies desktop, so an app can be installed and broken without touching a phone."
LABEL org.opencontainers.image.vendor="junkerderprovinz"
LABEL org.opencontainers.image.source="https://github.com/junkerderprovinz/strawknight"

# TITLE feeds the PWA manifest; SELKIES_UI_TITLE is the visible tab and sidebar
# title of the Selkies web client. Both must be set on this base.
#
# SELKIES_ENABLE_BASIC_AUTH=false: the Selkies server turns basic auth ON by
# default with well-known credentials (ubuntu / mypasswd). Same house fix as
# krusader and Crucible - no login unless CUSTOM_USER and PASSWORD are actually
# set, which init-nologin enforces by stripping the empty values Unraid passes
# for blank template fields.
ENV TITLE="StrawKnight" \
    SELKIES_UI_TITLE="StrawKnight" \
    SELKIES_ENABLE_BASIC_AUTH="false"

# ---------------------------------------------------------------------------
# Base tools. socat is not incidental: the emulator's adb binds to loopback
# only, so without a forwarder nothing outside the container can reach it and
# the entire point of the rig - deploying from Android Studio - is gone.
# ---------------------------------------------------------------------------
RUN set -eux; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates unzip xz-utils jq \
        socat \
        # wmctrl moves the emulator window back onto the screen when Selkies
        # resizes the desktop under it - see svc-window-keeper for why that
        # is not a one-off placement.
        wmctrl x11-utils \
        # Fonts, or the emulator window and xterm render text as empty boxes
        fontconfig fonts-noto fonts-noto-color-emoji fonts-dejavu-core \
        fonts-liberation2 \
        # Desktop background setter, used by rootfs/defaults/autostart
        feh \
        # openbox-xdg-autostart logs a complaint on every boot without this
        python3-xdg \
        locales; \
    fc-cache -f >/dev/null 2>&1 || true; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# ---------------------------------------------------------------------------
# A JDK, because sdkmanager is a Java program. Headless: nothing here opens a
# Java window, and the full JDK drags in a desktop toolkit for nothing.
# ---------------------------------------------------------------------------
RUN set -eux; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        openjdk-21-jdk-headless; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# ---------------------------------------------------------------------------
# The Android SDK.
#
# ANDROID_API 36 is Android 16, and it is the NEWEST on purpose.
#
# This started at 34, reasoning that Android 14 is where the six-hour daily cap
# on dataSync foreground services landed and a sync app has to survive exactly
# that. That was too cautious, and jdp said so. 15 keeps the cap AND adds a
# timeout on top, 16 keeps both, so the newest level is the STRICTEST rather
# than a different one - and the Play Store requires a recent target level for
# a new submission anyway. Testing against 14 would have been testing a rule
# more lenient than the one the app ships under.
#
# Only ONE level is installed, and that has a consequence the boot script has to
# handle: an AVD in the persistent volume points at a system image by path, so
# raising this number leaves the existing device pointing at an image that is no
# longer in the container. See init-strawknight, which notices and says so.
#
# google_apis rather than the plain AOSP image, because it carries Play services
# and a real DocumentsUI - the SAF file picker an app asks for a folder with. An
# image without one cannot answer whether the picker flow works at all.
#
# The command-line tools zip is version-pinned and checksum-verified. Google
# serves that URL forever and changes what is behind it, so an unpinned fetch is
# a build that silently becomes a different build.
# ---------------------------------------------------------------------------
ENV ANDROID_SDK_ROOT=/opt/android-sdk \
    ANDROID_HOME=/opt/android-sdk
ARG CMDLINE_TOOLS_VERSION=13114758
ARG CMDLINE_TOOLS_SHA256=7ec965280a073311c339e571cd5de778b9975026cfcbe79f2b1cdcb1e15317ee
ARG ANDROID_API=36
ARG ANDROID_ABI=x86_64
ARG ANDROID_TAG=google_apis
RUN set -eux; \
    zip="/tmp/cmdline-tools.zip"; \
    curl -fsSL -o "${zip}" \
        "https://dl.google.com/android/repository/commandlinetools-linux-${CMDLINE_TOOLS_VERSION}_latest.zip"; \
    echo "${CMDLINE_TOOLS_SHA256}  ${zip}" | sha256sum -c -; \
    mkdir -p "${ANDROID_SDK_ROOT}/cmdline-tools"; \
    unzip -q "${zip}" -d /tmp/cmdline; \
    mv /tmp/cmdline/cmdline-tools "${ANDROID_SDK_ROOT}/cmdline-tools/latest"; \
    rm -rf "${zip}" /tmp/cmdline
ENV PATH="${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin:${ANDROID_SDK_ROOT}/platform-tools:${ANDROID_SDK_ROOT}/emulator:${PATH}"

# The system image is the big one, roughly 3 GB, so it gets its own layer: a
# change to anything below must not make it download again.
RUN set -eux; \
    yes | sdkmanager --licenses >/dev/null; \
    sdkmanager --install \
        "platform-tools" \
        "emulator" \
        "platforms;android-${ANDROID_API}" \
        "system-images;android-${ANDROID_API};${ANDROID_TAG};${ANDROID_ABI}" >/dev/null; \
    # Prove the pieces the rig depends on are actually there rather than
    # trusting a silent installer: a missing emulator binary would otherwise
    # only surface as a container that starts and shows an empty desktop.
    test -x "${ANDROID_SDK_ROOT}/emulator/emulator"; \
    test -x "${ANDROID_SDK_ROOT}/platform-tools/adb"; \
    test -d "${ANDROID_SDK_ROOT}/system-images/android-${ANDROID_API}/${ANDROID_TAG}/${ANDROID_ABI}"; \
    rm -rf /root/.android/cache /tmp/*

# Which image the AVD is built from at first boot, recorded here so the boot
# script does not have to repeat the build arguments and drift from them.
ENV STRAWKNIGHT_PACKAGE="system-images;android-${ANDROID_API};${ANDROID_TAG};${ANDROID_ABI}" \
    STRAWKNIGHT_API="${ANDROID_API}"

# The AVD lives in the persistent volume, not in the image. It holds installed
# apps, granted permissions and anything a test wrote, and losing that on every
# container recreate would mean re-granting the SAF folder permission each time,
# which is one of the things being tested.
ENV ANDROID_AVD_HOME=/config/.android/avd \
    ANDROID_SDK_HOME=/config \
    ANDROID_USER_HOME=/config/.android

# ---------------------------------------------------------------------------
# Skeleton configs and s6-overlay init scripts
# ---------------------------------------------------------------------------
COPY rootfs/ /

# Suppress the base image's branding so the log ends on our own READY banner.
RUN set -eux; \
    : > /etc/s6-overlay/s6-rc.d/init-adduser/branding 2>/dev/null || true; \
    run=/etc/s6-overlay/s6-rc.d/init-adduser/run; \
    if [ -f "$run" ]; then \
        sed -i -e '/To support LSIO projects visit:/d' -e '\#linuxserver\.io/donate#d' "$run"; \
    fi

RUN chmod +x \
    /usr/local/bin/print-banner.sh \
    /usr/local/bin/sk \
    /etc/s6-overlay/s6-rc.d/init-nologin/run \
    /etc/s6-overlay/s6-rc.d/init-strawknight/run \
    /etc/s6-overlay/s6-rc.d/svc-emulator/run \
    /etc/s6-overlay/s6-rc.d/svc-adb-bridge/run \
    /etc/s6-overlay/s6-rc.d/svc-window-keeper/run \
    /etc/s6-overlay/s6-rc.d/svc-strawknight-ready/run \
    /defaults/autostart \
    /defaults/startwm.sh

# ---------------------------------------------------------------------------
# Browser-tab favicon. Same single-path mechanism the other house images use:
# init-nginx copies /usr/share/selkies/www/icon.png into favicon.ico on every
# start. Fail loudly if the path moves, because a silently missing icon is the
# kind of thing that gets noticed months later.
# ---------------------------------------------------------------------------
COPY assets/icon.png /usr/local/share/strawknight-icon.png
RUN set -eux; \
    dst=/usr/share/selkies/www/icon.png; \
    [ -f "$dst" ] || { echo "ERROR: $dst missing - the selkies base layout changed, update the branding override"; exit 1; }; \
    cp /usr/local/share/strawknight-icon.png "$dst"; \
    echo "strawknight: branded selkies icon at $dst"

COPY assets/wallpaper.png /usr/local/share/strawknight-wallpaper.png

ENV KEYBOARD_LAYOUT=us \
    GTK_THEME=Adwaita:dark \
    LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8

# How the emulator draws.
#
# swiftshader_indirect by default because it works everywhere, including a
# container with no GPU wired in at all. `host` is faster and is what makes
# scrolling read honestly, but it needs the nvidia runtime and /dev/dri; set it
# from the template once the GPU is confirmed.
# Where the read-only share lands. The `sk` helper looks here for an APK given
# by bare name, so `sk install arrowloop.apk` finds it without a path.
ENV SK_SHARE=/share

ENV EMULATOR_GPU=swiftshader_indirect \
    EMULATOR_DEVICE=pixel_6 \
    EMULATOR_RAM=2048 \
    EMULATOR_EXTRA_ARGS=""

# 6080 is deliberately NOT served here: the screen is Selkies on 3000/3001, and
# ADB is 5555. Two ways to see one screen would be two things to explain.
EXPOSE 5555

# Healthy means the WebUI answers AND the emulator is actually up. A rig whose
# desktop loads while the phone never booted looks fine and is useless.
HEALTHCHECK --interval=30s --timeout=15s --start-period=300s --retries=3 \
    CMD ["/bin/sh", "-c", "c=$(curl -ks -o /dev/null -w '%{http_code}' --max-time 5 https://127.0.0.1:${CUSTOM_HTTPS_PORT:-3001}/); [ \"$c\" != \"000\" ] || exit 1; [ \"$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\\r\\n')\" = \"1\" ] || exit 1"]
