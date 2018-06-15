Patchwork-FDO
=============

The missing link between mailing lists and CI.

Patchwork mainly:
 * picks up emails from the mailing list(s) and organizes them in projects and
   series
 * exports events through an API for each new series (for CI system consumption)
 * makes patches/series available as downloadable mboxes
 * provides API endpoint for submitting testing results
 * sends those results as a reply to the patch/series on the mailing list

And secondly:
 * provides a Web UI to browse, search and download the patches
 * give means of tracing patches state, from initial submission to acceptance

It **supplements** mailing lists, not replaces them.

How To?
-------

Check out `docs/` directory. You can find more details and installation guide
there.

This Is A Fork
--------------

FDO flavor of Patchwork was forked quite a while ago due to the original
project stagnancy. Since then, the original one picked up on development
speed, going in its own direction. You can check it out here:
<https://github.com/getpatchwork/patchwork>.

Links
-----

Official Patchwork-FDO repository: <https://gitlab.freedesktop.org/patchwork-fdo/patchwork-fdo/>

Freedesktop instance: <https://patchwork.freedesktop.org/>
