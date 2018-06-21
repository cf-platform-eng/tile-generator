# Tile Generator Examples
This directory contains examples of various types of tiles.

## Adding Examples
Each example should have a `build.sh` script that does whatever needs
to be done, and then calls `tile build`, passing through any
parameters. The Tile Generator CI pipeline expects this interface.

We plan to incrementally split aparat the large, one-of-everything
[sample tile](../sample) into several smaller example tiles that look
more like real product tiles.
