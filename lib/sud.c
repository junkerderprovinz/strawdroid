/*
 * The root half of ROOT=true, started as root over adb on every boot. Each
 * connection from su brings the caller's arguments and its stdin, stdout and
 * stderr; the command runs as root on those, and its exit status goes back.
 * The socket is abstract, so it needs no file an app could be denied.
 */
#include <signal.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/wait.h>
#include <unistd.h>

#include "sud.h"

#define SHELL "/system/bin/sh"

static int is_uid(const char *arg)
{
    return strcmp(arg, "root") == 0 ||
           (arg[0] != '\0' && strspn(arg, "0123456789") == strlen(arg));
}

/* "su -c <command>" as root managers take it, "su [uid] [command...]" as
 * Android's own su does, and a plain "su" reads commands from stdin. */
static void run(int argc, char **argv)
{
    for (int i = 0; i < argc; i++) {
        if (strcmp(argv[i], "-c") == 0 && i + 1 < argc)
            execl(SHELL, "sh", "-c", argv[i + 1], (char *)NULL);
        else if (argv[i][0] != '-' && !is_uid(argv[i]))
            execvp(argv[i], &argv[i]);
        else
            continue;
        _exit(127);
    }
    execl(SHELL, "sh", (char *)NULL);
    _exit(127);
}

static void serve(int conn)
{
    char payload[SUD_MAX_PAYLOAD + 1];
    char control[CMSG_SPACE(3 * sizeof(int))];
    struct iovec iov = {.iov_base = payload, .iov_len = SUD_MAX_PAYLOAD};
    struct msghdr msg = {.msg_iov = &iov, .msg_iovlen = 1,
                         .msg_control = control, .msg_controllen = sizeof(control)};
    struct cmsghdr *cmsg;
    char *argv[1024];
    int argc = 0, fds[3], status = 1;
    ssize_t len;
    pid_t pid;

    len = recvmsg(conn, &msg, 0);
    cmsg = CMSG_FIRSTHDR(&msg);
    if (len <= 0 || !cmsg || cmsg->cmsg_type != SCM_RIGHTS ||
        cmsg->cmsg_len != CMSG_LEN(sizeof(fds)))
        _exit(1);
    memcpy(fds, CMSG_DATA(cmsg), sizeof(fds));
    payload[len] = '\0';
    for (char *p = payload; p < payload + len && argc < 1023; p += strlen(p) + 1)
        if (*p)
            argv[argc++] = p;
    argv[argc] = NULL;

    pid = fork();
    if (pid == 0) {
        for (int i = 0; i < 3; i++)
            dup2(fds[i], i);
        close(conn);
        run(argc, argv);
    }
    if (pid > 0 && waitpid(pid, &status, 0) == pid)
        status = WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
    if (write(conn, &status, sizeof(status)) != sizeof(status))
        _exit(1);
    _exit(0);
}

int main(void)
{
    struct sockaddr_un addr = {.sun_family = AF_UNIX};
    int sock = socket(AF_UNIX, SOCK_STREAM, 0);

    memcpy(addr.sun_path + 1, SUD_SOCKET, strlen(SUD_SOCKET));
    if (sock < 0 ||
        bind(sock, (struct sockaddr *)&addr,
             offsetof(struct sockaddr_un, sun_path) + 1 + strlen(SUD_SOCKET)) != 0 ||
        listen(sock, 16) != 0)
        return 1;

    /* Detached, so it outlives the adb shell that started it. */
    if (daemon(0, 0) != 0)
        return 1;
    signal(SIGCHLD, SIG_IGN);
    setenv("PATH", "/product/bin:/apex/com.android.runtime/bin:/apex/com.android.art/bin:"
                   "/system_ext/bin:/system/bin:/system/xbin:/odm/bin:/vendor/bin:/vendor/xbin", 1);

    for (;;) {
        int conn = accept(sock, NULL, NULL);
        if (conn < 0)
            continue;
        if (fork() == 0) {
            close(sock);
            signal(SIGCHLD, SIG_DFL);
            serve(conn);
        }
        close(conn);
    }
}
