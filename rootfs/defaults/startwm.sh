#!/usr/bin/env bash
# Overrides the Selkies base image's /defaults/startwm.sh. The Nvidia/zink block
# makes the desktop's OpenGL, and with EMULATOR_GPU=host the emulator too, use
# the GPU once the nvidia container runtime has put /dev/dri into the container.

if which nvidia-smi > /dev/null 2>&1 && ls -A /dev/dri 2>/dev/null && [ "${DISABLE_ZINK}" == "false" ]; then
  export LIBGL_KOPPER_DRI2=1
  export MESA_LOADER_DRIVER_OVERRIDE=zink
  export GALLIUM_DRIVER=zink
fi

exec dbus-launch --exit-with-session /usr/bin/openbox-session
