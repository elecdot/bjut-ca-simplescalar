FROM khaledhassan/simplescalar:latest

RUN sed -i 's|archive.ubuntu.com|mirrors.tuna.tsinghua.edu.cn|g; s|security.ubuntu.com|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list && \
        apt-get update && \
        apt-get install -y \
        bash \
        sudo wget \
        git vim

WORKDIR /workspace
CMD [ "/bin/bash" ]
