# PCF Tile Generator

This is a tile generation utility for PCF tiles. Tiles are the
installation package format used by Pivotal's Ops Manager to deploy add-on
software such as services and their brokers, buildpacks, or anything else
that needs to be installable in both public and private cloud deployments.

The current release of the tile generator supports tiles that have any
combination of the following package types:
- Cloud Foundry Applications
- Cloud Foundry Buildpacks
- Cloud Foundry Service Brokers (both inside and outside the Elastic Runtime)
- Docker images (both inside and outside the Elastic Runtime)

## How to Use

1. Create a repository for your tile (preferably git, but this is not required)
2. Initialize it as a tile repo using `tile init`
3. Edit the `tile.yml` file to describe your tile (more detail below)
4. Build your tile using `tile build`

The generator will first create a BOSH release (in the `release` subdirectory),
then wrap that release into a Pivotal tile (in the `product` subdirectory).
If required for the installation, it will automatically pull down the latest
release version of the Cloud Foundry CLI.

## Describing your Tile

All required configuration for your tile is in the file called `tile.yml`.
`tile init` will create an initial version for you that can serve as a template.
The first section in the file describes the general properties of your tile:

```
name: tile-name # By convention lowercase with dashes
icon: resources/icon.png
label: Brief Text for the Tile Icon
description: Longer description of the tile's purpose
```

The `icon` should be a 128x128 pixel image that will appear on your tile in
the Ops Manager GUI. By convention, any resources used by the tile should be
placed in the `resources` sub-directory of your repo, although this is not
mandatory. The `label` test will appear on the tile under your icon.

### Packages

Next you can specify the packages to be included in your tile. The format of
the package entry depends on the type of package you are adding.

For a standard Cloud Foundry application (that is being 'cf push'ed into the
Elastic Runtime), use the following format:

<pre>
- name: my-application
  type: app                            <i># or app-broker (see below)</i>
  uri: app.example.com
  files:
  - path: resources/app1.jar
  start_command: start_here.sh         <i># optional</i>
  health_monitor: true                 <i># optional</i>
  create_open_security_group: true     <i># optional</i>
  org_quota: 2000                      <i># optional</i>
  memory: 1500                         <i># optional</i>
  persistence_store: true              <i># optional</i>
</pre>

If your application is also a service broker, use `app-broker` as the type
instead of just `app`. `persistence_store: true` results in the user being
able to select a backing service for data persistence.

For an external service broker, use:

<pre>
- name: my-application
  type: external-broker
  uri: http://broker3.example.com
  username: user
  password: <i>secret</i>
  internal_service_names: 'service1,service2'
</pre>


## Versioning

The tile generator uses semver versioning. By default, `tile build` will
generate the next patch release. Major and minor releases can be generated
by explicitly specifying `tile build major` or `tile build minor`. Or to
override the version number completely, specify a valid semver version on
the build command, e.g. `tile build 3.4.5`.

No-op content migration rules are generated for every prior release to the
current release, so that Ops Manager will allow tile upgrades from any
version to any newer version. This depends on the existence of the file
`tile-history.yml`. In a pinch, if you need to be able to upgrade from a
random old version to a new one, you can edit that file, or do:

```
tile build <old-version>
tile build <new-version>
```

The new tile will then support upgrades from `old-version`.

## Example

```
$ tile build
name: tibco-bwce
icon: icon.png
label: TIBCO BusinessWorks Container Edition
description: BusinessWorks edition that supports deploying to Cloud Foundry
version: 0.0.2

bosh init release
bosh generate package cf_cli
bosh generate package bwce_buildpack
bosh generate job install_bwce_buildpack
bosh generate job remove_bwce_buildpack
bosh create release --final --with-tarball --version 0.0.2

tile generate release
tile generate metadata
tile generate errand install_bwce_buildpack
tile generate errand remove_bwce_buildpack
tile generate content-migrations

created tile tibco-bwce-0.0.2.pivotal
```

This tile includes a single large buildpack, and takes less than 15 seconds
to build including the CF CLI download and the BOSH release generation.

## Supported Commands

```
init [<tile-name>]
build [patch|minor|major|<version>]
```

## Credits

- [sparameswaran](https://github.com/sparameswaran) supplied most of the actual template content, originally built as part of [cf-platform-eng/bosh-generic-sb-release](https://github.com/cf-platform-eng/bosh-generic-sb-release.git), except
- [frodenas](https://github.com/frodenas) contributed most of the docker content through [cloudfoundry-community/docker-boshrelease](https://github.com/cloudfoundry-community/docker-boshrelease.git)
- [joshuamckenty](https://github.com/joshuamckenty) suggested the jinja template approach he employed in [opencontrol](https://github.com/opencontrol)
