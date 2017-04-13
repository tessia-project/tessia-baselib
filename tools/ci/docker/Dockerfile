FROM ubuntu:latest

# by default we expect the git repo to be placed by the ci process under /assets
# but it is also possible to use this dockerfile directly and override the variables
# to point to another location
ARG git_repo=/assets/tessia_baselib.git

RUN apt-get update -q && \
    # Install the distro dependencies.
    # ATTENTION: make sure to keep a comment for each explaining why is it needed.
    DEBIAN_FRONTEND=noninteractive apt-get -yq install --no-install-recommends \
    # used to install python libraries
    python3-pip \
    # used by pbr (in setuptools) to detect module version numbers
    git \
    # these are needed to build cryptography (dep chain is tessia_baselib -> paramiko ->
    # cryptography)
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev && \
    # Install the python dependencies.
    # setuptools for installing applications (including tessia_baselib) - it must be installed
    # separately first otherwise other packages fail to install
    pip3 install -U setuptools && \
    # update the pip version if necessary
    pip3 install -U pip \
    # pbr is used by tessia_baselib for installation
    pbr \
    # dependencies used for testing builds
    pylint \
    coverage

COPY assets /assets/

# tessia_baselib installation
RUN cd /assets && \
    git clone $git_repo tessia_baselib && \
    cd tessia_baselib && \
    pip3 install -U -r requirements.txt && \
    ./setup.py install && \
    # files settings
    install -m 600 /usr/local/etc/tessia/* /etc/tessia && \
    rm -rf /usr/local/etc/tessia && \
    # remove unneeded dependencies used only for building paramiko and uwsgi
    DEBIAN_FRONTEND=noninteractive apt-get -yq purge --auto-remove \
        build-essential libssl-dev libffi-dev python3-dev

CMD ["/assets/entrypoint"]