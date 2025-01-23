Ansible and system names
------------------------
All managed systems are listed in `inventory.yaml`, to let Ansible know
where to find them and what hardware they use.

By default, Ansible deploys changes to all listed hosts. To deploy to
only hose, you can use the `--limit` option.

The inventory contains a `test-bbb` and `test-rockpi-s` entry, which are
intended to be used for local testing (will install both client and
backend).

Below, all commands use `--limit some_host` to run against a single host, make
sure to change that to whatever host you are working with.

Setting up a Beaglebone black
------------------
Start with a base Debian image, console or minimal flavor. At the time
of writing (2023-09), the official images only have a console flavor of
the outdated Debian 10 version. Rcn-ee.net has newer images, see:

https://forum.beagleboard.org/tag/latest-images

The BBB needs the armhf image (*not* ARM64), with the AM335x arch.

Above forum topic currently does not list the ARM335x armhf images for
Debian 12, but they are available for download at e.g.
https://rcn-ee.net/rootfs/release/2023-10-07/bookworm-minimal-armhf/
just not 100% final yet:
https://forum.beagleboard.org/t/bcm-module-beagle-bone-black-with-debian-bookworm/35490/6

Steps:
 - Flash image on SD card
 - Setup key authentication for root (login with debian:temppwd, create
   `/root/.ssh/authorized_keys` using sudo)
 - Reboot (to complete SD filesystem resize)
 - Add to inventory (or use existing maybe)
 - Run initial sync:

        ansible-playbook -i inventory.yaml playbook.yaml --limit bbb

Setting up a Rock Pi S
----------------------
Start with a base Debian image, CLI flavor (maybe minimal CLI also
works, not tested). Can be downloaded from:

  https://www.armbian.com/rockpi-s/

Steps:
 - Flash image on SD card
 - Login (with root:1234) and walk through the setup wizard (create user
   debian, passwords do not matter)
 - Setup key authentication for root (e.g. with ssh-copy-id)
 - Add to inventory (or use existing maybe)
 - Run initial sync:

        ansible-playbook -i inventory.yaml playbook.yaml --limit rockpi-s

Set up new backend
------------------
 - Run ansible for main setup
 - Create a new superuser

       /opt/doorlockd/django-backend$ poetry run ./manage.py createsuperuser

 - Put SSL fingerprint (shown in add new lock Django admin form) to lock
   client config.ini in this repository.

Set up new lock
---------------
 - Run ansible for main setup
 - Get the generated certificate by running:

       /opt/doorlockd/lock-client$ ./tools/gencert.sh client.pem

   (answer "N" for overwrite)
 - Create a new lock in the backend Django admin, add certificate.

Updating
--------
To update the client on all locks:

    ansible-playbook -i inventory.yaml playbook.yaml --limit locks --tags system,lock

To update the backend:

    ansible-playbook -i inventory.yaml playbook.yaml --limit backends --tags system,backend

To update everything:

    ansible-playbook -i inventory.yaml playbook.yaml --limit locks,backends

Set up NAT through USB (Beaglebone)
-----------------------------------
Enable NAT on your local system

    echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward
    sudo iptables -t nat -A POSTROUTING  -s 192.168.7.2 -j MASQUERADE

Enable routing over USB on the beaglebone:

    ansible-playbook -i inventory.yaml playbook.yaml --tags usb_route --limit bbb

This sets temporary config (until beaglebone is rebooted), to prevent
this default route from breaking connectivity later (e.g. when
the MASQUERADE is not set up anymore and you have an actual ethernet
connection available on the beaglebone).

Write to EMMC (Beaglebone)
--------------------------
To copy SD card installation to EMMC:

    ansible-playbook -i inventory.yaml playbook.yaml --tags flash_emmc --limit bbb
    ansible-playbook -i inventory.yaml playbook.yaml --tags reboot --limit bbb

The second command will raise an error because the board reboots
immediately.

To update Django (+ production_settings.py)
---------------------------------------------
Uodate only:

    ansible-playbook -i inventory.yaml playbook.yaml --limit backends --tags django
