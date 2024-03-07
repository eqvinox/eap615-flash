EAP615 firmware flash tool
==========================

This tool installs OpenWRT on a factory-fresh TP-Link EAP615-Wall wifi AP.

It might also work on EAP613, but this is **not tested**.

Since these types of devices are frequently used en masse for a larger install,
automating the OpenWRT install with a script like this may be helpful.


Requirements
------------

- DHCP (v4) server to assign an IP address

- OpenWRT `…-squashfs-factory.bin` image.  **Note TP-link firmware 1.1.7
  will refuse OpenWRT 23.05.2 and older, use snapshot images for now**


Invocation
----------

Connect the AP (isolation/no internet access is recommended, but not needed.
So far I've only seen the AP setting its clock with NTP, no other call-home
or automatic upgrading.  But this may change in future versions.)

Find out its IP address.  If you don't know how to do that
**you probably should not be doing this.**

Then:

```
python3 flash.py --debug --openwrt openwrt-ramips-mt7621-tplink_eap615-wall-v1-squashfs-factory.bin $IPADDR
```

The `--debug` option shows HTTP requests as they are executed.


Bugs & patches
--------------

I will **NOT** fix bugs in this tool.  You can fork the repo and fix them
yourself if needed.  If you send a PR I might accept it, or not, depending on
if I have time.

All my EAP615s are flashed now, so I can't really test this tool anymore.  By
its nature, it destroys its own testability ;)
