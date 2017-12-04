#!/usr/bin/env bash
# Copyright 2017 IBM Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -e

function build() {
    local root_pwd="$1"

    set -x
    apt-get update
    apt-get install -y debirf python3
    tar xzf /usr/share/doc/debirf/example-profiles/rescue.tgz

    # add our packages
    for include_pkg in s390-tools openssh-server multipath-tools kexec-tools net-tools; do
        echo -e "\n+$include_pkg" >> rescue/packages
    done

    # remove non s390x packages
    for remove_pkg in nvramtool grub2 inteltool msrtool dmidecode superiotool; do
        sed -i "/$remove_pkg/ d" rescue/packages
    done

    # add module to configure password
    if [ -n "$root_pwd" ] ; then
        cat > rescue/modules/b0_rootpwd <<EOF
#!/bin/sh -e

# debirf module: set root password

echo "root:$root_pwd" | chpasswd -R \${DEBIRF_ROOT}
EOF
        chmod a+x rescue/modules/b0_rootpwd
    fi

    # add module to set securetty
    cat > rescue/modules/b0_securetty <<EOF
#!/bin/sh -e

# debirf module: add securetty

echo sclp_line0 >> \${DEBIRF_ROOT}/etc/securetty
if [ -z "$root_pwd" ]; then
    echo ssh >> \${DEBIRF_ROOT}/etc/securetty
fi
EOF
    chmod a+x rescue/modules/b0_securetty

    # add module to set ssh config
    cat > rescue/modules/b0_ssh_config <<EOF
#!/bin/sh -e

# debirf module: set ssh config

echo "PermitRootLogin yes" >> \${DEBIRF_ROOT}/etc/ssh/sshd_config
echo "PermitEmptyPasswords yes" >> \${DEBIRF_ROOT}/etc/ssh/sshd_config
EOF
    chmod a+x rescue/modules/b0_ssh_config

    # add module to create missing device files
    cat > rescue/modules/b0_set_dev <<EOF
#!/bin/sh -e

# debirf module: create dev files

mknod -m 666 \${DEBIRF_ROOT}/dev/console c 5 1 || true
for i in \$(seq 0 7); do
    mknod -m 660 \${DEBIRF_ROOT}/dev/loop\$i b 7 \$i || true
done
EOF
    chmod a+x rescue/modules/b0_set_dev

    # add module to copy install disk script
    cat > rescue/modules/b0_copy_script <<EOF
#!/bin/sh -e

# debirf module: copy install disk script

cp $(which liveimg-to-disk) \${DEBIRF_ROOT}/usr/local/bin
EOF
    chmod a+x rescue/modules/b0_copy_script

    echo "DEBIRF_KERNEL_FLAVOR=s390x" >> rescue/debirf.conf
    # -r (real chroot) is needed until https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=855234 gets fixed
    debirf make --no-warning -r rescue

    mv rescue/*cgz rescue/initrd
    mv rescue/vmlinu* rescue/kernel

    # generate addrsize file
    initrd_size=$(stat -c%s rescue/initrd)
    python3 -c "import sys, struct; buffer = struct.pack('>IIII', 0, 0x02000000, 0, $initrd_size); sys.stdout.buffer.write(buffer)" > rescue/initrd.addrsize

    # generate ins file
    cat > rescue/live-img.ins <<EOF
* tessia live image
kernel 0x00000000
initrd 0x02000000
parmfile 0x00010480
initrd.addrsize 0x00010408
EOF

    # generate parmfile
    echo 'cio_ignore=all,!condev' > rescue/parmfile

    # pack everything up
    tar zcvf live-image.tgz -C rescue kernel initrd initrd.addrsize parmfile live-img.ins

    # move tarball inside the initrd and re-generate it
    mv live-image.tgz rescue/root/usr/local/share
    debirf make --no-warning -i rescue
    mv rescue/*cgz rescue/initrd

    # re-generate addrsize file
    initrd_size=$(stat -c%s rescue/initrd)
    python3 -c "import sys, struct; buffer = struct.pack('>IIII', 0, 0x02000000, 0, $initrd_size); sys.stdout.buffer.write(buffer)" > rescue/initrd.addrsize

    # final packaging
    tar zcvf live-image.tgz -C rescue kernel initrd initrd.addrsize parmfile live-img.ins

    echo "tarball bootstrap process completed at $(pwd)/live-image.tgz"
}

usage() {
    echo "Usage: $(basename $0) [OPTION]"
    echo "Build the tessia live image tarball"
    echo ""
    echo "OPTIONs:"
    echo "  -p           image's root password"
    echo "  -h           show this help"
}

while getopts :hp: option; do
    case "$option" in
        h)
            usage
            exit 0
            ;;
        p)
            root_pwd="$OPTARG"
            ;;
        :)
            echo "error: missing argument for -$OPTARG" >&2
            usage
            exit 1
            ;;
        ?)
            echo "error: invalid option -$OPTARG" >&2
            usage
            exit 1
            ;;
    esac
done

build "$root_pwd"
