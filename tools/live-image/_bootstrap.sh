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
    local build_id="$2"

    set -x
    apt-get update
    apt-get install -y debirf python3

    # create live image structure
    mkdir -p rescue/modules
    for module in a0_add_extra_repos a0_add_security_repos a0_motd install-manpages mdadm network root-bashrc z0_remove-locales z1_clean-root; do
        ln -s /usr/share/debirf/modules/$module rescue/modules/$module
    done
    # make some changes here
    cp /usr/share/debirf/modules/a0_prep-root rescue/modules/a0_prep-root
    sed -i -e 's/--force-yes/--allow-downgrades --allow-remove-essential --allow-change-held-packages/'  rescue/modules/a0_prep-root
    sed -i -e '/apt-get/ s/$/ || :/'  rescue/modules/a0_prep-root

    cp /usr/share/debirf/modules/install-kernel rescue/modules/install-kernel
    sed -i -e '/install kernel deb/ a\cp "${DEBIRF_KERNEL_PACKAGE/image/modules}" "$DEBIRF_ROOT"/var/cache/apt/archives/' rescue/modules/install-kernel
    sed -i -e '/dpkg --extract/ a\debirf_exec dpkg --unpack /var/cache/apt/archives/"${KPKG/image/modules}" ' rescue/modules/install-kernel

    # add our packages
    for include_pkg in bonnie++ cryptsetup eject ethtool hdparm hfsplus hfsutils initramfs-tools-core kexec-tools lsof lsscsi lvm2 mtd-utils multipath-tools net-tools openssh-server parted pciutils rsync s390-tools sg3-utils socat squashfs-tools wget; do
        echo "+$include_pkg" >> rescue/packages
    done

    # add configuration
    echo DEBIRF_LABEL="debirf-rescue" > rescue/debirf.conf

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

    # make the image smaller, manpages are not necessary
    rm -f rescue/modules/install-manpages

    # add live image git version to login prompt
    sed -i -e "/^EOF/ i echo Tessia live-img $build_id" rescue/modules/root-bashrc

    # use the newest kernel available
    suite=$(lsb_release --codename --short)
    apt-get update
    kernel_pkg=$(apt-cache show linux-image-generic | grep '^Depends: ' | sed 's/^Depends: //' | tr ',' '\n' | tr -d ' ' | grep ^linux-image | sort -V -r | head -1)
    ( cd rescue && apt-get download $kernel_pkg ${kernel_pkg/image/modules} )
    echo "DEBIRF_KERNEL_PACKAGE=$(realpath rescue/linux-image-*.deb)" >> rescue/debirf.conf

    echo "DEBIRF_MIRROR=http://ports.ubuntu.com/ubuntu-ports" >> rescue/debirf.conf

    # -r (real chroot) is needed until https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=855234 gets fixed
    debirf make --no-warning -r rescue

    mv rescue/*cgz rescue/initrd
    mv rescue/vmlinu* rescue/kernel

    # generate addrsize file
    initrd_size=$(stat -c%s rescue/initrd)
    kernel_size=$(stat -c%s rescue/kernel)
    # round up kernel size to 16 MB
    initrd_offset=$(python3 -c "print(format(($kernel_size | 0x00ffffff) + 1, '#010x'))")
    python3 -c "import sys, struct; buffer = struct.pack('>QQ', $initrd_offset, $initrd_size); sys.stdout.buffer.write(buffer)" > rescue/initrd.addrsize

    # generate ins file
    sed -e "s/INITRD_OFFSET/$initrd_offset/" > rescue/live-img.ins <<EOF
* tessia live image $build_id
kernel 0x00000000
initrd INITRD_OFFSET
parmfile 0x00010480
initrd.addrsize 0x00010408
EOF

    # generate parmfile
    echo 'cio_ignore=all,!condev' > rescue/parmfile

    # pack everything up
    tar zcvf live-image.tgz -C rescue kernel initrd initrd.addrsize parmfile live-img.ins

    # move tarball inside the initrd and re-generate it
    mv live-image.tgz rescue/root/usr/local/share
    debirf make --no-warning -r -i rescue
    mv rescue/*cgz rescue/initrd

    # re-generate addrsize file
    initrd_size=$(stat -c%s rescue/initrd)
    python3 -c "import sys, struct; buffer = struct.pack('>QQ', $initrd_offset, $initrd_size); sys.stdout.buffer.write(buffer)" > rescue/initrd.addrsize

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
    echo "  -n           build id"
    echo "  -h           show this help"
}

while getopts :hp:n: option; do
    case "$option" in
        h)
            usage
            exit 0
            ;;
        p)
            root_pwd="$OPTARG"
            ;;
        n)
            build_id="$OPTARG"
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

build "$root_pwd" "$build_id"
