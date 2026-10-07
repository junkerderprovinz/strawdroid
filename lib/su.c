/*
 * su for ROOT=true. Android starts apps with no_new_privs, so a setuid su can
 * never make an app root. Like Magisk's, this one is only a client: it hands
 * its arguments and its stdin, stdout and stderr to strawdroid-sud, which runs
 * as root, and exits with the status of whatever the daemon ran.
 */
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

#include "sud.h"

int main(int argc, char **argv)
{
    char payload[SUD_MAX_PAYLOAD];
    size_t len = 0;
    int sock, fds[3] = {0, 1, 2}, status;
    struct sockaddr_un addr = {.sun_family = AF_UNIX};
    char control[CMSG_SPACE(sizeof(fds))] = {0};
    struct iovec iov = {.iov_base = payload};
    struct msghdr msg = {.msg_iov = &iov, .msg_iovlen = 1,
                         .msg_control = control, .msg_controllen = sizeof(control)};
    struct cmsghdr *cmsg;

    for (int i = 1; i < argc; i++) {
        size_t n = strlen(argv[i]) + 1;
        if (len + n > sizeof(payload)) {
            fputs("su: arguments too long\n", stderr);
            return 1;
        }
        memcpy(payload + len, argv[i], n);
        len += n;
    }
    iov.iov_len = len ? len : 1;
    if (!len)
        payload[0] = '\0';

    cmsg = CMSG_FIRSTHDR(&msg);
    cmsg->cmsg_level = SOL_SOCKET;
    cmsg->cmsg_type = SCM_RIGHTS;
    cmsg->cmsg_len = CMSG_LEN(sizeof(fds));
    memcpy(CMSG_DATA(cmsg), fds, sizeof(fds));

    memcpy(addr.sun_path + 1, SUD_SOCKET, strlen(SUD_SOCKET));
    sock = socket(AF_UNIX, SOCK_STREAM, 0);
    if (sock < 0 || connect(sock, (struct sockaddr *)&addr,
                            offsetof(struct sockaddr_un, sun_path) + 1 + strlen(SUD_SOCKET)) != 0) {
        fputs("su: the StrawDroid root daemon is not running\n", stderr);
        return 1;
    }
    if (sendmsg(sock, &msg, 0) < 0 || shutdown(sock, SHUT_WR) != 0 ||
        read(sock, &status, sizeof(status)) != sizeof(status))
        return 1;
    return status;
}
