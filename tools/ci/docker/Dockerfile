FROM ubuntu:22.04

# by default we expect the git repo to be placed by the ci process under /assets
# but it is also possible to use this dockerfile directly and override the variables
# to point to another location
ARG git_repo=/assets/tessia-baselib.git

RUN apt-get update -q && \
    # Install the distro dependencies.
    # ATTENTION: make sure to keep a comment for each explaining why is it needed.
    DEBIAN_FRONTEND=noninteractive apt-get -yq install --no-install-recommends \
    # used to install python libraries
    python3-pip python3-distutils \
    # used by pbr (in setuptools) to detect module version numbers
    git \
    # required to install rustup
    curl \
    # these are needed to build cryptography (dep chain is paramiko -> cryptography)
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev && \
    # Install the python dependencies.
    # setuptools for installing python applications - it must be installed first
    # separately otherwise other packages fail to install
    pip3 install -U setuptools && \
    # update the pip version if necessary
    pip3 install -U pip

RUN curl https://sh.rustup.rs -sSf | bash -s -- -y

ENV PATH="/root/.cargo/bin:${PATH}"
ENV CARGO_HOME="/root/.cargo"
ENV RUSTUP_HOME="/root/.rustup"

RUN cargo --version && rustc --version

COPY assets /assets/

# library installation
RUN cd /assets && \
    git clone $git_repo tessia-baselib && \
    cd tessia-baselib && \
    pip3 install -U -r requirements.txt -r dev-requirements.txt . && \
    # remove unneeded dependencies used only for building paramiko and uwsgi
    DEBIAN_FRONTEND=noninteractive apt-get -yq purge --auto-remove \
        build-essential libssl-dev libffi-dev python3-dev

CMD ["/assets/entrypoint"]
