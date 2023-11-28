Setting up a Beaglebone black
------------------
Start with a base Debian image, console or minimal flavor. At the time
of writing (2023-09), the official images only have a console flavor of
the outdated Debian 10 version. Rcn-ee.net has newer images, see:

https://forum.beagleboard.org/tag/latest-images

Though currently that only lists arm64 images for Debian 12, but the
armhf images are available at e.g.
https://rcn-ee.net/rootfs/release/2023-08-05/bookworm-minimal-armhf/
just not 100% final yet:
https://forum.beagleboard.org/t/bcm-module-beagle-bone-black-with-debian-bookworm/35490/6

Steps:
 - Flash image on SD card
 - Setup key authentication for root (login with debian:temppwd, create
   `/root/.ssh/authorized_keys` using sudo)
 - Add to inventory (or use existing maybe)
 - Run initial sync:

        ansible-playbook -i inventory.yaml playbook.yaml --limit test

Set up new manager
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

       /opt/doorlockd/lock-client$ ./tools/gencert.sh data/client.pem

   (answer "N" for overwrite)
 - Create a new lock in the manager Django admin, add certificate.

Set up NAT through USB (Beaglebone)
-----------------------------------
Enable NAT on your local system

    echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward
    sudo iptables -t nat -A POSTROUTING  -s 192.168.7.2 -j MASQUERADE

Enable routing over USB on the beaglebone:

    ansible-playbook -i inventory.yaml playbook.yaml --tags usb_route --limit test

This sets temporary config (until beaglebone is rebooted), to prevent
this default route from breaking connectivity later (e.g. when
the MASQUERADE is not set up anymore and you have an actual ethernet
connection available on the beaglebone).
