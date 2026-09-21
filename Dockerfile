# syntax=docker/dockerfile:1.27
#
# StrawDroid: the real Android emulator, the same AVD Android Studio starts,
# with its screen on a Selkies desktop, so an app under development can be
# installed, driven and broken without an APK ever touching a phone.
#
# Android-in-a-container (ReDroid, Waydroid) runs the Android userspace on the
# host kernel with no battery, motion sensor or power HAL. Doze never fires,
# WorkManager runs more eagerly than on real hardware, and Android's limits on
# dataSync foreground services never kick in, so a background sync app would
# pass tests it should fail. A real AVD enforces them, and
# `dumpsys deviceidle force-idle` triggers Doze on demand.
#
# budtmo/docker-android streams its screen through x11vnc and noVNC, which
# smears scrolling and transitions. Here the emulator sits on the same
# hardware-encoded Selkies/WebRTC desktop as the other house images.
#
# It follows the krusader image: LinuxServer's Selkies base, s6-overlay init,
# the HTTPS WebUI on 3001 and no login by default. GPU wiring is supplied at
# `docker run` by the Unraid template, which keeps the image vendor-neutral.
# The flavour is pinned rather than :latest or the floating :dev tag.
ARG BASE_TAG=ubunturesolute
FROM ghcr.io/linuxserver/baseimage-selkies:${BASE_TAG}

LABEL maintainer="junkerderprovinz"
LABEL org.opencontainers.image.title="strawdroid"
LABEL org.opencontainers.image.description="StrawDroid - a real Android emulator on a Selkies desktop, so an app can be installed and broken without touching a phone."
LABEL org.opencontainers.image.vendor="junkerderprovinz"
LABEL org.opencontainers.image.source="https://github.com/junkerderprovinz/strawdroid"

# TITLE feeds the PWA manifest and SELKIES_UI_TITLE the web client's tab and
# sidebar; this base needs both.
#
# The Selkies server enables basic auth by default, with well-known credentials
# (ubuntu / mypasswd). With SELKIES_ENABLE_BASIC_AUTH=false there is no login
# unless CUSTOM_USER and PASSWORD are set, and init-nologin strips the empty
# values Unraid passes for blank template fields.
ENV TITLE="StrawDroid" \
    SELKIES_UI_TITLE="StrawDroid" \
    SELKIES_ENABLE_BASIC_AUTH="false"

# The emulator's adb binds to loopback only, so socat forwards it; without it
# Android Studio cannot reach the device.
RUN set -eux; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates unzip xz-utils jq \
        socat \
        # svc-window-keeper uses wmctrl to move the emulator window back on
        # screen whenever Selkies resizes the desktop.
        wmctrl x11-utils \
        # Without fonts the emulator window and xterm render text as empty boxes.
        fontconfig fonts-noto fonts-noto-color-emoji fonts-dejavu-core \
        fonts-liberation2 \
        # Sets the desktop background, see rootfs/defaults/autostart.
        feh \
        # openbox-xdg-autostart logs a complaint on every boot without it.
        python3-xdg \
        locales; \
    fc-cache -f >/dev/null 2>&1 || true; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# sdkmanager is a Java program. The headless JDK spares the desktop toolkit.
RUN set -eux; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        openjdk-21-jdk-headless; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# API 36 is Android 16, the newest and also the strictest level: 14 added the
# six-hour daily cap on dataSync foreground services, 15 a timeout on top, and
# 16 keeps both. The Play Store requires a recent target level for new apps
# anyway.
#
# Only one level is installed. An AVD in the persistent volume points at its
# system image by path, so raising this number strands an existing device;
# init-strawdroid detects that and moves it aside.
#
# google_apis rather than plain AOSP, because it carries Play services and a
# real DocumentsUI, the SAF picker an app asks for a folder with.
#
# The command-line tools zip is pinned and checksum-verified, because Google
# changes what is behind a URL without changing the URL.
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

# The system image is roughly 3 GB, so it gets its own layer that later changes
# do not invalidate.
RUN set -eux; \
    yes | sdkmanager --licenses >/dev/null; \
    sdkmanager --install \
        "platform-tools" \
        "emulator" \
        "platforms;android-${ANDROID_API}" \
        "system-images;android-${ANDROID_API};${ANDROID_TAG};${ANDROID_ABI}" >/dev/null; \
    # sdkmanager can fail silently, and a missing emulator binary would
    # otherwise only show up as an empty desktop.
    test -x "${ANDROID_SDK_ROOT}/emulator/emulator"; \
    test -x "${ANDROID_SDK_ROOT}/platform-tools/adb"; \
    test -d "${ANDROID_SDK_ROOT}/system-images/android-${ANDROID_API}/${ANDROID_TAG}/${ANDROID_ABI}"; \
    rm -rf /root/.android/cache /tmp/*

# init-strawdroid builds the AVD from this package, so it cannot drift from the
# build arguments.
ENV STRAWDROID_PACKAGE="system-images;android-${ANDROID_API};${ANDROID_TAG};${ANDROID_ABI}" \
    STRAWDROID_API="${ANDROID_API}"

# The AVD lives in the persistent volume. It holds installed apps and granted
# permissions, among them the SAF folder permission under test, which a
# container recreate would otherwise reset.
ENV ANDROID_AVD_HOME=/config/.android/avd \
    ANDROID_SDK_HOME=/config \
    ANDROID_USER_HOME=/config/.android

# The Pixel Launcher cannot hide its search bar, leaves the app drawer out of
# themed icons and reads no icon packs, so svc-branding installs Lawnchair with
# Arcticons. Both APKs, about 90 MB, are fetched at build time with pinned
# versions and digests. Lawnchair is Apache-2.0 and Arcticons GPL-3.0; both ship
# unmodified as separate APKs and are credited in the README.
#
# Lawnchair's file name does not follow its tag (v15.0.0-beta3.0 against
# Lawnchair.15.0.0.Beta.3.0.apk), so both are given rather than one derived.
ARG LAWNCHAIR_TAG=v15.0.0-beta3.0
ARG LAWNCHAIR_FILE=Lawnchair.15.0.0.Beta.3.0.apk
ARG LAWNCHAIR_SHA=d4200d0985169fd79ba1bd225d653f2a2fe7b50aa07cb0d05ca64c7623f86059
ARG ARCTICONS_VERSION=15.0.5
ARG ARCTICONS_SHA=1bca18ec58c75f8a30a301996a403330e1e2ccab7df325aeb5f7e941dc5b79fe

RUN set -eux; \
    mkdir -p /defaults/apk; \
    curl -fsSL -o /defaults/apk/lawnchair.apk \
      "https://github.com/LawnchairLauncher/lawnchair/releases/download/${LAWNCHAIR_TAG}/${LAWNCHAIR_FILE}"; \
    echo "${LAWNCHAIR_SHA}  /defaults/apk/lawnchair.apk" | sha256sum -c -; \
    curl -fsSL -o /defaults/apk/arcticons.apk \
      "https://github.com/Donnnno/Arcticons/releases/download/${ARCTICONS_VERSION}/Arcticons-${ARCTICONS_VERSION}-normal-release.apk"; \
    echo "${ARCTICONS_SHA}  /defaults/apk/arcticons.apk" | sha256sum -c -; \
    ls -l /defaults/apk

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
    /etc/s6-overlay/s6-rc.d/init-strawdroid/run \
    /etc/s6-overlay/s6-rc.d/svc-emulator/run \
    /etc/s6-overlay/s6-rc.d/svc-adb-bridge/run \
    /etc/s6-overlay/s6-rc.d/svc-window-keeper/run \
    /etc/s6-overlay/s6-rc.d/svc-share-mirror/run \
    /etc/s6-overlay/s6-rc.d/svc-strawdroid-ready/run \
    /etc/s6-overlay/s6-rc.d/svc-branding/run \
    /defaults/autostart \
    /defaults/startwm.sh

# init-nginx copies /usr/share/selkies/www/icon.png into favicon.ico on every
# start. The build fails if the base moves that path.
COPY assets/icon.png /usr/local/share/strawdroid-icon.png
RUN set -eux; \
    dst=/usr/share/selkies/www/icon.png; \
    [ -f "$dst" ] || { echo "ERROR: $dst missing, the selkies base layout changed; update the branding override"; exit 1; }; \
    cp /usr/local/share/strawdroid-icon.png "$dst"; \
    echo "strawdroid: branded selkies icon at $dst"

COPY assets/wallpaper.png /usr/local/share/strawdroid-wallpaper.png

ENV KEYBOARD_LAYOUT=us \
    GTK_THEME=Adwaita:dark \
    LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8

# The `sk` helper looks here for an APK given by bare name.
ENV SK_SHARE=/share

# swiftshader_indirect works everywhere, even with no GPU wired in. `host` is
# faster and shows how an app really scrolls, but needs the nvidia runtime and
# /dev/dri; set it from the template once the GPU is confirmed.
ENV EMULATOR_GPU=swiftshader_indirect \
    EMULATOR_DEVICE=pixel_6 \
    EMULATOR_RAM=2048 \
    EMULATOR_EXTRA_ARGS=""

# No noVNC on 6080: the screen is Selkies on 3000/3001, and ADB is 5555.
EXPOSE 5555

# Healthy needs the WebUI and a booted Android; a desktop without a phone is
# useless here.
HEALTHCHECK --interval=30s --timeout=15s --start-period=300s --retries=3 \
    CMD ["/bin/sh", "-c", "c=$(curl -ks -o /dev/null -w '%{http_code}' --max-time 5 https://127.0.0.1:${CUSTOM_HTTPS_PORT:-3001}/); [ \"$c\" != \"000\" ] || exit 1; [ \"$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\\r\\n')\" = \"1\" ] || exit 1"]
