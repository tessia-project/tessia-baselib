# Release notes

## 0.2.1 (2018-03-18)

### Fixes

- zvm: increase timeout while waiting for initrd file to be punched during netboot
- zvm: raise PermissionsError when login failed due to invalid credentials

## 0.2.0 (2018-03-13)

### New features

- Add support to manage z/VM guests ([#1](https://gitlab.com/tessia-project/tessia-baselib/issues/1)):
    - Boot (IPL) guest with CMS, or from a DASD or SCSI-FCP disk;
    - Boot (IPL) guest with Linux from a network URL (kernel/initrd);
    - Issue console commands and upload files to the guest.
- Add capability to set CPUs' type dynamically during LPAR activation ([#4](https://gitlab.com/tessia-project/tessia-baselib/issues/4))

### Improvements

- Provide detailed information from HMC API when an LPAR activation fails ([#5](https://gitlab.com/tessia-project/tessia-baselib/issues/5)).

## 0.1.0 (2018-01-12)

### New features

- Initial release
- Add support to manage LPARs in HMC classic mode
    - Boot (IPL) LPAR from a DASD or SCSI-FCP disk;
    - Boot (IPL) LPAR with Linux from a network URL (kernel/initrd) using an auxiliar disk.
- Add support to manage zKVM guests
    - Boot (IPL) guest from a DASD or SCSI-FCP disk;
    - Boot (IPL) guest with Linux from a network URL (kernel/initrd).
- Add support to perform actions on a Linux system (via SSH):
    - upload files
    - issues commands
