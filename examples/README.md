Making a deploy tarball.
================

This is intended to make this process easier (almost automatic).

To do so, create a symlink called `tor` from the safest-assessment directory
to whatever version of Tor you want to use. Currently it has a
sim-link to ~cwacek/bin/tor.

Then run `bash mk-tarball.sh safest-assessment .`.
safest-assessment.tar.gz will be placed in this directory.


Complicated Use
-----------

More complicated use may require modification to the files
inside safest-assessment. You can use them as an example.
