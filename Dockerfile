FROM khaledhassan/simplescalar:latest

RUN sed -i 's|archive.ubuntu.com|mirrors.tuna.tsinghua.edu.cn|g; s|security.ubuntu.com|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list && \
        apt-get update && \
        apt-get install -y \
        bash \
        sudo wget \
        git vim tmux

RUN apt-get install -y \
        python3 python3-pip \
        python3-yaml python3-pandas python3-matplotlib

# 标记容器环境，便于 Makefile 判断是否需要通过 docker 代理
ENV INSIDE_SIM_DOCKER=1

WORKDIR /workspace
CMD [ "/bin/bash" ]
