# Pushing Apps to CF

The tile-generator can be used to push apps running on CF. An associated package entry for the application should exist in the tile.yml file and be marked as type: `app`. Bosh errands would be created to push or delete the app on CF as part of install and delete of the tile.

The package would be treated as an application type with the deploy and delete app errands even if the package is specified of type `app` or `app-broker`, `docker-app` or `docker-app-broker`.

### Properties format
Various properties can be specified to control/configure the app. The format is

<table>
  <tr align="left">
    <th> Field </th>
    <th> Required </th>
    <th> Type </th>
    <th> Description </th>
    <th> Default </th>
  </tr>
  <tr>
    <td> name </td>
    <td> Y </td>
    <td> string </td>
    <td> name of application </td>
    <td>  </td>
  </tr>
  <tr>
    <td> type </td>
    <td> Y </td>
    <td> string </td>
    <td> denotes its an app type </td>
    <td> can be `app` or `app-broker` or `docker-app` </td>
  </tr>
  <tr>
    <td> uri </td>
    <td> Y </td>
    <td> string </td>
    <td> Uri/Route for the app on CF </td>
    <td> </td>
  </tr>
  <tr>
    <td> start_command </td>
    <td> N </td>
    <td> string </td>
    <td> custom start command </td>
    <td> Go with the docker or buildpack generated start command as default </td>
  </tr>
  <tr>
    <td> health_monitor </td>
    <td> N </td>
    <td> boolean </td>
    <td> Turn off health monitoring of apps on CF </td>
    <td> true </td>
  </tr>
  <tr>
    <td> org </td>
    <td> N </td>
    <td> string </td>
    <td> target org to deploy; if not specified, new org would be created </td>
    <td>  </td>
  </tr>
  <tr>
    <td> space </td>
    <td> N </td>
    <td> string </td>
    <td> target space to deploy; if not specified, new space would be created </td>
    <td>  </td>
  </tr>
  <tr>
    <td> org_quota </td>
    <td> N </td>
    <td> integer </td>
    <td> size of org quota (if we are creating brand new org) in MB  </td>
    <td> 1024 </td>
  </tr>
  <tr>
    <td> bind_to_service </td>
    <td> N </td>
    <td> comma separated set of strings </td>
    <td> List of pre-provisioned Services to bind the app in the given org/space; needs org & space to be specified  </td>
    <td> 'none' </td>
  </tr>
  <tr>
    <td> memory </td>
    <td> N </td>
    <td> integer </td>
    <td> size of memory (in MB) for app </td>
    <td> 512 </td>
  </tr>
  <tr>
    <td> create_open_security_group </td>
    <td> N </td>
    <td> boolean </td>
    <td> Open up app security group for outbound access </td>
    <td> false </td>
  </tr>
  <tr>
    <td> persistence_store </td>
    <td> N </td>
    <td> boolean </td>
    <td> App needs to bind to MySQL or Mongo service; Drop down UI option would be generated if set to true </td>
    <td> 'none' </td>
  </tr>
  <tr>
    <td> files </td>
    <td> Y if app or app-broker </td>
    <td> string </td>
    <td> Relative path to file containing the app bits  </td>
    <td>  </td>
  </tr>
  <tr>
    <td> image </td>
    <td> Y if docker-app or docker-app-broker </td>
    <td> string </td>
    <td> docker image uri on public docker registry  </td>
    <td>  </td>
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
