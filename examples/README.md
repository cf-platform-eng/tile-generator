# Tile Generator Examples
This directory contains examples of various types of tiles.

## Adding Examples
Each example should have a `build.sh` script that does whatever needs
to be done, and then calls `tile build`, passing through any
parameters. The Tile Generator CI pipeline expects this interface.

We plan to incrementally split aparat the large, one-of-everything
[sample tile](../sample) into several smaller example tiles that look
more like real product tiles.

## Naming Convention
- To make it clear in Ops Manager that these are test tiles, not to
  beconfused with real Pivotal or partner products, please prefix the
  `label` field in the tile.yml with "Test".

- To keep them from cluttering up Tile Dashboard, please prefix the
  `name` field in tile.yml with "z-test".

- Even though these tiles will only ever show up for admins of PivNet,
  please use prepend "Z" to the product name on PivNet.
