FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y systemd systemd-sysv

RUN (cd /lib/systemd/system/sysinit.target.wants/; for i in *; do [ $i == systemd-tmpfiles-setup.service ] || rm -f $i; done); \
    rm -f /lib/systemd/system/multi-user.target.wants/*;\
    rm -f /lib/systemd/system/graphical.target.wants/*; \
    ln -sf /lib/systemd/system/multi-user.target /lib/systemd/system/default.target;

VOLUME [ "/sys/fs/cgroup" ]

CMD ["/lib/systemd/systemd"]
