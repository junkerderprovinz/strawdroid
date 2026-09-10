#!/usr/bin/env bash
# Overrides the Selkies base image's /defaults/startwm.sh.
#
# HOUSE RULE - the "<APP> IS READY" banner, printed by svc-strawknight-ready
# once the desktop serves and Android has booted, MUST be the LAST block in
# `docker logs`. The desktop session prints continuously; if its stdout stays on
# the service's stdio, its output trails past the READY banner and the log no
# longer ends on it. So the session goes to /dev/null, exactly as the stock base
# script does and as krusader and the Crucible sandbox do.
#
# Do NOT remove this redirect to "keep the session log visible" - un-redirect it
# only while actively debugging the desktop, then put it back.
#
# Identical to the base script otherwise, including the Nvidia/zink block, which
# is what makes the desktop's own OpenGL use the box's GPU once the nvidia
# container runtime has put /dev/dri inside. That matters more here than in a
# browser sandbox: with EMULATOR_GPU=host the emulator renders through this same
# stack, and it is the difference between judging how an app scrolls and
# guessing.

# Enable Nvidia GPU support if detected
if which nvidia-smi > /dev/null 2>&1 && ls -A /dev/dri 2>/dev/null && [ "${DISABLE_ZINK}" == "false" ]; then
  export LIBGL_KOPPER_DRI2=1
  export MESA_LOADER_DRIVER_OVERRIDE=zink
  export GALLIUM_DRIVER=zink
fi

exec dbus-launch --exit-with-session /usr/bin/openbox-session
