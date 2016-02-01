# Pushing Apps to CF

The tile-generator can be used to push apps running on CF. An associated package entry for the application should exist in the tile.yml file and be marked as type: `app`. Bosh errands would be created to push or delete the app on CF as part of install and delete of the tile.

The package would be treated as an application type with the deploy and delete app errands even if the package is specified of type `app` or `app-broker`, `docker-app` or `docker-app-broker`.

### Properties format
Various properties can be specified to control/configure the app. The format is

<table>
  <tr>
    <th> Field </th>
    <th> Required </th>
    <th> Type </th>
    <th> Description </th>
    <th> Default </th>
  </tr>
  <tr>
    <th> name </th>
    <th> Y </th>
    <th> string </th>
    <th> name of application </th>
    <th>  </th>
  </tr>
  <tr>
    <th> type </th>
    <th> Y </th>
    <th> string </th>
    <th> denotes its an app type </th>
    <th> can be `app` or `app-broker` or `docker-app` </th>
  </tr>
  <tr>
    <th> uri </th>
    <th> Y </th>
    <th> string </th>
    <th> Uri/Route for the app on CF </th>
    <th> </th>
  </tr>
  <tr>
    <th> start_command </th>
    <th> N </th>
    <th> string </th>
    <th> custom start command </th>
    <th> Go with the docker or buildpack generated start command as default </th>
  </tr>
  <tr>
    <th> health_monitor </th>
    <th> N </th>
    <th> boolean </th>
    <th> Turn off health monitoring of apps on CF </th>
    <th> true </th>
  </tr>
  <tr>
    <th> org </th>
    <th> N </th>
    <th> string </th>
    <th> target org to deploy; if not specified, new org would be created </th>
    <th>  </th>
  </tr>
  <tr>
    <th> space </th>
    <th> N </th>
    <th> string </th>
    <th> target space to deploy; if not specified, new space would be created </th>
    <th>  </th>
  </tr>
  <tr>
    <th> org_quota </th>
    <th> N </th>
    <th> integer </th>
    <th> size of org quota (if we are creating brand new org) in MB  </th>
    <th> 1024 </th>
  </tr>
  <tr>
    <th> bind_to_service </th>
    <th> N </th>
    <th> comma separated set of strings </th>
    <th> List of pre-provisioned Services to bind the app in the given org/space; needs org & space to be specified  </th>
    <th> 'none' </th>
  </tr>
  <tr>
    <th> memory </th>
    <th> N </th>
    <th> integer </th>
    <th> size of memory (in MB) for app </th>
    <th> 512 </th>
  </tr>
  <tr>
    <th> create_open_security_group </th>
    <th> N </th>
    <th> boolean </th>
    <th> Open up app security group for outbound access </th>
    <th> false </th>
  </tr>
  <tr>
    <th> persistence_store </th>
    <th> N </th>
    <th> boolean </th>
    <th> App needs to bind to MySQL or Mongo service; Drop down UI option would be generated if set to true </th>
    <th> 'none' </th>
  </tr>
  <tr>
    <th> files </th>
    <th> Y if app or app-broker </th>
    <th> string </th>
    <th> Relative path to file containing the app bits  </th>
    <th>  </th>
  </tr>
  <tr>
    <th> image </th>
    <th> Y if docker-app or docker-app-broker </th>
    <th> string </th>
    <th> docker image uri on public docker registry  </th>
    <th>  </th>
  </tr>
</table>

### Sample package
```
packages:
- name: app1
  type: app
  uri: app1                          # Provide only host/route name, app domain would be automatically added to host during deploy
  start_command: start_here.sh       # Custom start command
  create_open_security_group: true
  # Following three entries (org, space, bind_to_service) need to be defined together
  # in order to look a pre-existing service in a specified target org/space
  org: dev-org
  space: dev-space
  # Provide names of pre-provisioned service  (comma separated)
  bind_to_service: "mysql-service,TestService"
  # org_quota only applicable if a new org is being created fresh
  org_quota: 1024
  memory: 500
  files:
  - path: resources/app1.jar
- name: app2
  type: app
  health_monitor: false              # Turn off health monitoring, default: true
  files:
  - path: resources/app2.jar
  persistence_store: true            # Users will be allowed to select between MySQL, Mongo or none

```
