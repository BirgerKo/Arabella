# Multi-arch dnsmasq image (linux/arm64 + linux/amd64).
# alpine:3.21 ships native ARM64 and x86-64 variants.
FROM alpine:3.21
RUN apk add --no-cache dnsmasq
ENTRYPOINT ["dnsmasq", "--keep-in-foreground", "--log-facility=-"]
