# Deploying Brokers to CF

The tile-generator can be used to register brokers on CF. An associated package entry for the broker should exist in the tile.yml file and be marked as type: ` external-broker` , `app-broker` or `docker-app-broker`. Bosh errands would be created to register or destroy the service broker on CF as part of install and delete of the tile.

The package can be an application pushed to CF and also working as a Service Broker or it can be completely an external service broker to CF. No files need to be specified in case of an external broker.

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
    <td> Name of Service Broker </td>
    <td>  </td>
  </tr>
  <tr>
    <td> type </td>
    <td> Y </td>
    <td> string </td>
    <td> denotes its an app type </td>
    <td> can be `external-broker` or `app-broker` or `docker-app-broker`</td>
  </tr>
  <tr>
    <td> uri </td>
    <td> Y  </td>
    <td> string </td>
    <td> Relative Uri/Route for the app on CF if its also an app or fully qualified domain for external broker </td>
    <td> </td>
  </tr>
  <tr>
    <td> on_demand_service_plans </td>
    <td> N  </td>
    <td> string </td>
    <td> List of attributes that can be used to generate plans on the fly under one service type (like license keys, some remote host/endpoint, attributes required for the plan in the service broker) in case of broker being pushed to CF </td>
    <td> </td>
  </tr>
  <tr>
    <td> username </td>
    <td> Y only for external broker </td>
    <td> string </td>
    <td> Username to authenticate the broker </td>
    <td>  </td>
  </tr>
  <tr>
    <td> password </td>
    <td> Y only for external broker </td>
    <td> string </td>
    <td> Password to authenticate the broker </td>
    <td>  </td>
  </tr>
  <tr>
    <td> internal_service_names </td>
    <td> N </td>
    <td> comma separated string </td>
    <td> Comma separate list of service names to enable access on marketplace</td>
    <td>  </td>
  </tr>
</table>

### Sample Broker packages
```
# Type of app-broker with support for on_demand_service_plans
- name: broker2
  type: app-broker
  files:
  - path: resources/broker2.jar
  on_demand_service_plans:
  # name and guid fields are supplied by default
  # add additional fields here:
  - name: description
    type: string
    descrp: "Some Description"
    configurable: true
  - name: key1
    type: integer
    descrp: "Key 1 of type integer"
    configurable: true
  - name: key2
    type: string
    descrp: "Key 2 of type string"
    configurable: true
# External broker that has uri, user/password
- name: broker3
  type: external-broker
  uri: http://broker3.example.com
  username: user
  password: secret
  internal_service_names: 'service1,service2'
```
