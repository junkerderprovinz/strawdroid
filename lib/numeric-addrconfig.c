/*
 * Preloaded into the emulator so its modem comes up on a Docker network.
 *
 * qemu reaches the emulator's modem simulator at ::1 and resolves that address
 * with AI_ADDRCONFIG. glibc then drops every IPv6 result unless some interface
 * other than loopback has an IPv6 address, and Docker networks usually have
 * IPv6 switched off. The modem never connects, Android sees no SIM, and calls
 * and SMS do not work. For a numeric address there is nothing for
 * AI_ADDRCONFIG to decide, so the flag is dropped for those and kept for names.
 */
#define _GNU_SOURCE
#include <arpa/inet.h>
#include <dlfcn.h>
#include <netdb.h>

int getaddrinfo(const char *node, const char *service,
                const struct addrinfo *hints, struct addrinfo **res)
{
    static int (*next)(const char *, const char *,
                       const struct addrinfo *, struct addrinfo **);
    unsigned char addr[sizeof(struct in6_addr)];

    if (!next)
        next = dlsym(RTLD_NEXT, "getaddrinfo");

    if (node && hints && (hints->ai_flags & AI_ADDRCONFIG) &&
        (inet_pton(AF_INET6, node, addr) == 1 ||
         inet_pton(AF_INET, node, addr) == 1)) {
        struct addrinfo numeric = *hints;
        numeric.ai_flags &= ~AI_ADDRCONFIG;
        return next(node, service, &numeric, res);
    }
    return next(node, service, hints, res);
}
