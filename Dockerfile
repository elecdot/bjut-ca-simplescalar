FROM khaledhassan/simplescalar:latest

RUN sed -i 's|archive.ubuntu.com|mirrors.tuna.tsinghua.edu.cn|g; s|security.ubuntu.com|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list && \
        apt-get update && \
        apt-get install -y \
        bash \
        sudo wget \
        git vim tmux \
        python3 python3-pip python3-venv && \
        pip3 install --no-cache-dir pyyaml pandas matplotlib

# 标记容器环境，便于 Makefile 判断是否需要通过 docker 代理
ENV INSIDE_SIM_DOCKER=1

WORKDIR /workspace
CMD [ "/bin/bash" ]
