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

## Screencast

For a 7-minute introduction into what it is and does, see [this screencast]
(https://www.youtube.com/watch?v=_WeJbqNJWzQ).

## How to Use

1. Create a repository for your tile (preferably git, but this is not required)
2. Initialize it as a tile repo using `tile init`
3. Edit the `tile.yml` file to describe your tile (more detail below)
4. Build your tile using `tile build`

The generator will first create a BOSH release (in the `release` subdirectory),
then wrap that release into a Pivotal tile (in the `product` subdirectory).
If required for the installation, it will automatically pull down the latest
release version of the Cloud Foundry CLI.

## Install Dependencies

```
pip install -r requirements.txt
```

## Describing your Tile

All required configuration for your tile is in the file called `tile.yml`.
`tile init` will create an initial version for you that can serve as a template.
The first section in the file describes the general properties of your tile:

```
name: tile-name # By convention lowercase with dashes
icon_file: resources/icon.png
label: Brief Text for the Tile Icon
description: Longer description of the tile's purpose
```

The `icon_file` should be a 128x128 pixel image that will appear on your tile in
the Ops Manager GUI. By convention, any resources used by the tile should be
placed in the `resources` sub-directory of your repo, although this is not
mandatory. The `label` test will appear on the tile under your icon.

### Packages

Next you can specify the packages to be included in your tile. The format of
the package entry depends on the type of package you are adding.

#### Pushed Application

For a standard Cloud Foundry application (that is being 'cf push'ed into the
Elastic Runtime), use the following format:

<pre>
- name: my-application
  type: app                            <i># or app-broker (see below)</i>
  uri: app.example.com
  files:
  - path: resources/my-application.jar
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

#### Service Brokers

Most modern service brokers are pushed into the Elastic Runtime as normal
CF applications. For these types of brokers, use the Pushed Application format
specified above, but set the type to `app-broker` instead of just `app`.

Some service brokers support operator-defined service plans, for isntance when
the plans reflect customer license keys. To allow operators to add plans from
the tile configuration, add the following section to the service broker definition:

<pre>
  on_demand_service_plans:
  - name: description
    type: string
    descrp: "Some Description"
    configurable: true
  - name: key1
    type: integer
    descrp: "Key 1 of type integer"
    configurable: true
  - name: key2
    type: secret
    descrp: "Key 2 of type Password"
    configurable: true
</pre>

Name and GUID fields will be supplied by default for each plan, but all other fields
are optional and customizable.

For an external service broker, use:

<pre>
- name: my-application
  type: external-broker
  uri: http://broker3.example.com
  username: user
  password: <i>secret</i>
  internal_service_names: 'service1,service2'
</pre>

#### Buildpacks

<pre>
- name: my-buildpack
  type: buildpack
  files:
  - path: resources/buildpack.zip
</pre>

#### Docker Images

Applications packages as docker images can be deployed inside or outside the Elastic
Runtime. To push a docker image as a CF application, use the `docker-app` type:

<pre>
- name: docker-app
  type: docker-app
  image: test/dockerimage
  uri: docker-app1.example.com
  start_command: start_here.sh
  health_monitor: true
  create_open_security_group: true
  org_quota: 2000
  memory: 1500
</pre>

If this app is also a service broker, use `docker-app-broker` instead of just
`docker-app`. This option is appropriate for docker-wrapper 12-factor apps that
delegate their persistence to bound services.

Docker applications that require persistent storage can not be deployed into the
Elastic Runtime. These can be deployed to separate BOSH-managed VMs instead by
using the `docker-bosh` type:

<pre>
- name: docker-bosh1
  type: docker-bosh
  image: test/dockerimage
  cpu: 5
  memory: 4096
  ephemeral_disk: 4096
  persistent_disk: 2048
  instances: 1
  manifest: |
    test-key1: testValue1
    test-key2: testValue2
    test-key3: testValue3
    test-key4: testValue4
    containers:
    - name: redis
      image: "redis"
      command: "--dir /var/lib/redis/ --appendonly yes"
      bind_ports:
      - "6379:6379"
      bind_volumes:
      - "/var/lib/redis"
      entrypoint: "redis-server"
      memory: "256m"
      env_vars:
      - "EXAMPLE_VAR=1"
    - name: mysql
      image: "google/mysql"
      bind_ports:
      - "3306:3306"
      bind_volumes:
      - "/mysql"
    - name: elasticsearch
      image: "bosh/elasticsearch"
      links:
      - mysql:db
      depends_on:
      - mysql
      bind_ports:
      - "9200:9200"
</pre>

### Custom Forms and Properties

...

### Stemcells

The tile generator will default to a recent stemcell supported by Ops Manager.
In most cases the default will be fine, as the stemcell is only used to execute
CF command lines and/or the docker daemon. But if you have specific stemcell
requirements, you can override the defaults in your `tile.yml` file by including
a `stemcell-criteria` section and replacing the appopriate values:

<pre>
stemcell_criteria:
  os: 'ubunty-trusty'
  version: '3146.5'     <i>NOTE: Your must quote the version to force the type to be string</i>
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

## Gotchas

If you include a docker-bosh package type, your tile will have a dependency on
[cloudfoundry-community/docker-boshrelease](https://github.com/cloudfoundry-community/docker-boshrelease.git). Tile Generator will automatically attempt to build and include a release of
that software in your tile. Unfortunately, that build has a lot of Ruby dependencies
and is not likely to succeed on first attempt. The best way to resolve build issues
in this area is to do it manually:

```
cd docker-boshrelease
./update
bosh create release
```

After that succeeds, tile-generator should be able to build its release file without
further issues.

## Credits

- [sparameswaran](https://github.com/sparameswaran) supplied most of the actual template content, originally built as part of [cf-platform-eng/bosh-generic-sb-release](https://github.com/cf-platform-eng/bosh-generic-sb-release.git)
- [frodenas](https://github.com/frodenas) contributed most of the docker content through [cloudfoundry-community/docker-boshrelease](https://github.com/cloudfoundry-community/docker-boshrelease.git)
- [joshuamckenty](https://github.com/joshuamckenty) suggested the jinja template approach he employed in [opencontrol](https://github.com/opencontrol)
