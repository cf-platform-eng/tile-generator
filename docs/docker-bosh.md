# Deploying Brokers to CF

The tile-generator can be used to manage and run docker images using Bosh Jobs (not on CF). An associated package entry for the broker should exist in the tile.yml file and be marked as type: ` docker-bosh`. Bosh jobs would be created to upload the docker image and run the docker image as a job within Bosh.

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
    <td> Name of Docker Job </td>
    <td>  </td>
  </tr>
  <tr>
    <td> type </td>
    <td> Y </td>
    <td> string </td>
    <td> denotes its a docker bosh type </td>
    <td> docker-bosh </td>
  </tr>
  <tr>
    <td> files </td>
    <td> Y  </td>
    <td> string </td>
    <td> Relative path to a docker image in form of zipped tar ball (tgz) </td>
    <td> </td>
  </tr>
  <tr>
    <td> image_name </td>
    <td> Y  </td>
    <td> string </td>
    <td> name of the docker image </td>
    <td> </td>
  </tr>
  <tr>
    <td> cpu </td>
    <td> Y  </td>
    <td> integer </td>
    <td> number of virtual cpus to allot for running the docker image </td>
    <td> </td>
  </tr>
  <tr>
    <td> memory </td>
    <td> Y  </td>
    <td> integer </td>
    <td> memory for the docker image in MB</td>
    <td> </td>
  </tr>
  <tr>
    <td> ephemeral_disk </td>
    <td> Y  </td>
    <td> integer </td>
    <td> size of ephemeral (non-persistent) disk for the docker image </td>
    <td> </td>
  </tr>
  <tr>
    <td> persistent_disk </td>
    <td> Y  </td>
    <td> integer </td>
    <td> size of persistent disk for the docker image </td>
    <td> </td>
  </tr>
  <tr>
    <td> instances </td>
    <td> Y  </td>
    <td> integer </td>
    <td> number of vm instances to run the docker image </td>
    <td> 1 </td>
  </tr>
  <tr>
    <td> manifest </td>
    <td> Y </td>
    <td> yaml </td>
    <td> docker-boshrelease yaml manifest [1] for running the container; Also, requires specifying env variables to be passed onto the docker image along with the `image` name that matches the `image_name`.
    <td>  </td>
  </tr>
</table>

[1] [Properties format](https://github.com/cloudfoundry-community/docker-boshrelease/blob/master/CONTAINERS.md#properties-format)

### Sample docker package
```
- name: docker-bosh1
  type: docker-bosh
  image_name: ubuntu  # Need this to match the `image` specifed in manifest
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
      - "test_key1=testValue1"
      - "test_key2=testValue2"
      # Add custom properties below 
      - "custom_variable_name=(( .properties.customer_name.value ))"
      - "custom_variable_city=(( .properties.city.value ))"

```

If there are any custom properties that need to be passed as env variable to the docker image, specify those under the env-vars entry of the manifest. If the properties are dynamic and specified by user input, use the `((.properties.<propName>.value ))` syntax to propagate the value from custom forms to the manifest.

Also, specify the bind_ports and bind_volumes to expose ports and mount volumes from the VM.
