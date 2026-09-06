FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

RUN apt-get update && apt-get install -y \
    locales \
    git \
    zip \
    unzip \
    openjdk-17-jdk \
    python3 \
    python3-pip \
    python3-setuptools \
    autoconf \
    libtool \
    pkg-config \
    zlib1g-dev \
    libncurses5-dev \
    libncursesw5-dev \
    libtinfo5 \
    cmake \
    libffi-dev \
    libssl-dev \
    build-essential \
    ccache \
    && locale-gen en_US.UTF-8

RUN useradd -m -s /bin/bash builder
USER builder
WORKDIR /home/builder/app

ENV PATH="/home/builder/.local/bin:${PATH}"

# Install tested, compatible buildozer and Cython versions
RUN pip3 install --no-cache-dir --user --upgrade pip wheel setuptools
RUN pip3 install --no-cache-dir --user "cython<3.0.0" buildozer

# Run the build directly inside the container's isolated storage
CMD ["sh", "-c", "yes | buildozer android debug"]