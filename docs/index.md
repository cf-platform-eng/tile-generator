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

For a 7-minute introduction into what it is and does, see
[this screencast](https://www.youtube.com/watch?v=_WeJbqNJWzQ).

## Continuous Integration

The master branch of this repository is being monitored by
[this Concourse pipeline](https://dragon.somegood.org/pipelines/tile-generator).
The pipeline verifies that:

- The tile generator passes all unit tests in `lib/*_unittest.py`
- The tile generator successfully builds the sample tile in `sample`
- The generated tile passes all acceptance tests in `ci/acceptance-tests`
- The generated tile successfully deploys to a current version of PCF
- The deployed tile passes all deployment tests in `ci/deployment-tests`

## How to Use

1. Check out the tile-generator repo:

    ```bash
    git clone https://github.com/cf-platform-eng/tile-generator.git
    ```

2. Change to the root directory of the tile generator, and pull down the generator's dependencies:

    ```bash
    cd tile-generator
    pip install -r requirements.txt
    ```

3. Add the `bin` directory of tile-generator to your path:

    ```bash
    export PATH=`pwd`/bin:$PATH
    ```

    *If you expect to frequently use the tile generator, you may want to add this to your shell's startup script, i.e. `.profile`*

4. Install the [BOSH CLI](https://bosh.io/docs/bosh-cli.html)

5. Then, from within the root directory of the project for which you wish to create a tile, initialize it as a tile repo (we recommend that this be a git repo, but this is not required):

    ```bash
    cd <your project dir>
    tile init
    ```
   
6. Edit the generated `tile.yml` file to define your tile (more details below)

7. Build your tile

    ```bash
    tile build
    ```

The generator will first create a BOSH release (in the `release` subdirectory),
then wrap that release into a Pivotal tile (in the `product` subdirectory).
If required for the installation, it will automatically pull down the latest
release version of the Cloud Foundry CLI.

## Building the Sample

The repository includes a sample tile that exercises most of the features of the
tile generator (it is used by the CI pipeline to verify that things work correctly).
You can build this sample using the following steps:

```bash
cd sample
src/build.sh
tile build
```

The sample tile includes a Python application that is re-used in several packages,
sometimes as an app, sometimes as a service broker. One of the deployments (app3)
uses the sample application inside a docker image that is currently only modified
by the CI pipeline. If you modify the sample app, you will have to build your own
docker image using the provided `Dockerfile` and change the image name in
`sample/tile.yml` to include the modified code in app3.

## Defining your Tile

All required configuration for your tile is in the file called `tile.yml`.
`tile init` will create an initial version for you that can serve as a template.
The first section in the file describes the general properties of your tile:

```yaml
name: tile-name # By convention lowercase with dashes
icon_file: resources/icon.png
label: Brief Text for the Tile Icon
description: Longer description of the tile's purpose
```

The `icon_file` should be a 128x128 pixel image that will appear on your tile in
the Ops Manager GUI. By convention, any resources used by the tile should be
placed in the `resources` sub-directory of your repo, although this is not
mandatory. The `label` text will appear on the tile under your icon.

### Packages

Next you can specify the packages to be included in your tile. The format of
each package entry depends on the type of package you are adding.

#### Pushed Applications

Applications (including service brokers) that are being `cf push`ed into the
Elastic Runtime use the following format:

<pre>
- name: my-application
  type: app <i>or</i> app-broker
  manifest:
    <i># any options that you would normally specify in a cf manifest.yml, including</i>
    buildpack:
    command:
    domain:
    host:
    instances:
    memory:
    path:
    env:
    services:
  health_check: none                 <i># optional</i>
  configurable_persistence: true     <i># optional</i>
  needs_cf_credentials: true         <i># optional</i>
  auto_services: p-mysql p-redis     <i># optional</i>
</pre>

Note: for applications that are normally pushed as multiple files (node.js for example)
you should zip up the project files plus all dependencies into a single zip file, then
edit tile.yml to point to the zipped file: 

```bash
cd <your project dir>
zip -r resources/<your project name>.zip <list of file and dirs to include in the zip>
```

If your application is a service broker, use `app-broker` as the type instead of just
`app`. The application will then automatically be registered as a broker on install,
and deleted on uninstall.

`health_check` lets you configure the value of the cf cli `--health_check_type`
option. Expect this option to move into the manifest as soon as CF supports it there.
Currently, the only valid options are `none` and `port`.

`configurable_persistence: true` results in the user being able to select a backing
service for data persistence. If there is a specific broker you want to use, you can
use the `auto-services` feature described below. If you want to bind to an already
existing service instance, use the `services` proeprty of the `manifest` instead.

`needs_cf_credentials` causes the application to receive two additional environment
variables named `CF_ADMIN_USER` and `CF_ADMIN_PASSWORD` with the admin credentials
for the Elastic Runtime into which they are being deployed. This allows apps and
services to interact with the Cloud Controller.

`auto_services` is described in more detail below.

#### Service Brokers

Most modern service brokers are pushed into the Elastic Runtime as normal
CF applications. For these types of brokers, use the Pushed Application format
specified above, but set the type to `app-broker` or `docker-app-broker` instead
of just `app` or `docker-app`.

Some service brokers support operator-defined service plans, for instance when
the plans reflect customer license keys. To allow operators to add plans from
the tile configuration, add the following section:

<pre>
dynamic_service_plans:
- name: description
  type: string
  description: "Some Description"
  configurable: true
- name: key1
  type: integer
  description: "Key 1 of type integer"
  configurable: true
- name: key2
  type: secret
  description: "Key 2 of type Password"
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
Runtime. To push a docker image as a CF application, use the *Pushed Application*
format specified above, but use the `docker-app` or `docker-app-broker` type instead
of just `app` or `app-broker`. The docker image to be used is then specified using
the `image` property:

<pre>
- name: app1
  type: docker-app
  image: test/dockerimage
  manifest:
    ...
</pre>

If this app is also a service broker, use `docker-app-broker` instead of just
`docker-app`. This option is appropriate for docker-wrapped 12-factor apps that
delegate their persistence to bound services.

Docker applications that require persistent storage can not be deployed into
the Elastic Runtime. These can be deployed to separate BOSH-managed VMs instead
by using the `docker-bosh` type:

<pre>
- name: docker-bosh1
  type: docker-bosh
  cpu: 5
  memory: 4096
  ephemeral_disk: 4096
  persistent_disk: 2048
  instances: 1
  manifest: |
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
If a docker image cannot be downloaded by BOSH dynamically, its better to provide a ready made docker image and package it as part of the BOSH release. In that case, specify the image as a local file.
<pre>
- name: docker-bosh2
  type: docker-bosh
  files:
  - path: resources/cfplatformeng-docker-tile-example.tgz
  cpu: 5
  memory: 4096
  ephemeral_disk: 4096
  persistent_disk: 2048
  instances: 1
  manifest: |
    containers:
    - name: test_docker_image
      image: "cfplatformeng/docker-tile-example"
      env_vars:
      - "EXAMPLE_VAR=1"
      # See below on custom forms/variables and binding it to the docker env variable
      - "custom_variable_name=((.properties.customer_name.value))"
</pre>

Also, refer to [docker-bosh](docs/docker-bosh.md) for more details.

### Custom Forms and Properties

You can pass custom properties to all applications deployed by your tile by adding
the to the properties section of `tile.yml`:

```
properties:
- name: author
  type: string
  label: Author
  value: Tile Ninja
```

If you want the properties to be configurable by the tile installer, place them on
a custom for instead:

```
forms:
- name: custom-form1
  label: Test Tile
  description: Custom Properties for Test Tile
  properties:
  - name: customer_name
    type: string
    label: Full Name
  - name: street_address
    type: string
    label: Street Address
    description: Address to use for junk mail
  - name: city
    type: string
    label: City
  - name: zip_code
    type: string
    label: ZIP+4
    default: '90310'
  - name: country
    type: dropdown_select
    label: Country
    options:
    - name: country_us
      label: US
      default: true
    - name: country_elsewhere
      label: Elsewhere
```

Properties defined in either section will be passed to all pushed applications
as environment variables (the name of the environment variable will be the same
as the property name but in ALL_CAPS). They can also be referenced in other parts
of the configuration file by using `(( .properties.<property-name> ))` instead
of a hardcoded value.

### Automatic Provisioning of Services

Tile generator automates the provisioning of services. Any application (including
service brokers and docker-based applications) that are being pushed into the
Elastic Runtime can automatically be bound to services through the `auto_services`
feature:

<pre>
- name: app1
  type: app
  auto_services:
  - name: p-mysql
    plan: 100mb-dev
  - name: p-redis
</pre>

You can specify any number of service names, optionally specifying a specific
plan. During deployment, the generated tile will create an instance of each
service if one does not already exist, and then bind that instance to your
package.

Service instances provisioned this way survive updates, but will be deleted
when the tile is uninstalled.

*NOTE* that the name is the name of the provided *service*, *not* the *broker*.
In many cases these are not the same, and a single broker may even offer
multiple services. Use `cf marketplace` to see the services and plans
available from installed brokers.

If you do not specify a plan, the tile generator will use the first plan
listed for the service in the broker catalog. It is a good idea to always
specify a service plan. If you *change* the plan between versions of your
tile, the tile generator will attempt to update the plan while preserving
the service (thus not causing data loss during upgrade). If the service
does not support plan changes, this will cause the upgrade to fail.

`configurable_persistence` is really just a special case of `auto_services`,
letting the user choose between some standard brokers.

### Declaring Product Dependencies

When your product has dependencies on others, you can have Ops Manager
enforce that dependency by declaring it in your `tile.yml` file as follows:

```
requires_product_versions:
- name: p-mysql
  version '~> 1.7'
```

If the required product is not present in the PCF installation, Ops Manager
will display a message saying
`<your-tile> requires 'p-mysql' version '~> 1.7' as a dependency`, and will
refuse to install your tile until that dependency is satisfied.

When using automatic provisioning of services as described above, it is
often appropriate to add those products as a dependency. Tile generator can
not do this automatically as it can't always determine which product provides
the requested service.

### Orgs and Spaces

By default, the tile generator will create a single new org and space for any
packages that install into the Elastic Runtime, using the name of the tile and
appending `-org` and `-space`, respectively. The default memory quota for a
newly created or will be 1024 (1G). You can change any of these defaults by
specifying the following properties in `tile.yml`:

<pre>
org: test-org
org_quota: 4096
space: test-space
</pre>

### Security

If your cf packages need outbound access (including access to other packages
within the same tile), you will need to apply an appropriate security group.
The following option will remove all constraints on outbound traffic:

<pre>
apply_open_security_group: true
</pre>

### Stemcells

The tile generator will default to a recent stemcell supported by Ops Manager.
In most cases the default will be fine, as the stemcell is only used to execute
CF command lines and/or the docker daemon. But if you have specific stemcell
requirements, you can override the defaults in your `tile.yml` file by including
a `stemcell-criteria` section and replacing the appopriate values:

<pre>
stemcell_criteria:
  os: 'ubunty-trusty'
  version: '3146.5'     <i>NOTE: You must quote the version to force the type to be string</i>
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

```bash
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

- [sparameswaran](https://github.com/sparameswaran) supplied most of the actual template content, originally built as part of [cf-platform-eng/bosh-generic-sb-release](https://github.com/cf-platform-eng/bosh-generic-sb-release.git)
- [frodenas](https://github.com/frodenas) contributed most of the docker content through [cloudfoundry-community/docker-boshrelease](https://github.com/cloudfoundry-community/docker-boshrelease.git)
- [joshuamckenty](https://github.com/joshuamckenty) suggested the jinja template approach he employed in [opencontrol](https://github.com/opencontrol)
