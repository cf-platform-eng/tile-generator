# Deploying Brokers to CF

The tile-generator can be used to manage and run docker images using Bosh Jobs (not on CF). An associated package entry for the broker should exist in the tile.yml file and be marked as type: ` docker-bosh`. Bosh jobs would be created to upload the docker image and run the docker image as a job within Bosh.

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
    <th> Name of Docker Job </th>
    <th>  </th>
  </tr>
  <tr>
    <th> type </th>
    <th> Y </th>
    <th> string </th>
    <th> denotes its a docker bosh type </th>
    <th> docker-bosh </th>
  </tr>
  <tr>
    <th> files </th>
    <th> Y  </th>
    <th> string </th>
    <th> Relative path to a docker image in form of zipped tar ball (tgz) </th>
    <th> </th>
  </tr>
  <tr>
    <th> image_name </th>
    <th> Y  </th>
    <th> string </th>
    <th> name of the docker image </th>
    <th> </th>
  </tr>
  <tr>
    <th> cpu </th>
    <th> Y  </th>
    <th> integer </th>
    <th> number of virtual cpus to allot for running the docker image </th>
    <th> </th>
  </tr>
  <tr>
    <th> memory </th>
    <th> Y  </th>
    <th> integer </th>
    <th> memory for the docker image in MB</th>
    <th> </th>
  </tr>
  <tr>
    <th> ephemeral_disk </th>
    <th> Y  </th>
    <th> integer </th>
    <th> size of ephemeral (non-persistent) disk for the docker image </th>
    <th> </th>
  </tr>
  <tr>
    <th> persistent_disk </th>
    <th> Y  </th>
    <th> integer </th>
    <th> size of persistent disk for the docker image </th>
    <th> </th>
  </tr>
  <tr>
    <th> instances </th>
    <th> Y  </th>
    <th> integer </th>
    <th> number of vm instances to run the docker image </th>
    <th> 1 </th>
  </tr>
  <tr>
    <th> manifest </th>
    <th> Y </th>
    <th> yaml </th>
    <th> docker-boshrelease yaml manifest for running the container; Also, requires specifying env variables to be passed onto the docker image along with the `image` name that matches the `image_name`.
    <th>  </th>
  </tr>
</table>

### Sample docker package
```
- name: docker-bosh1
  type: docker-bosh
  image_name: ubuntu  # Need this to match the `image` specifed in manifest
  files:
  - path: resources/ubuntu_image.tgz
  cpu: 5
  memory: 4096
  ephemeral_disk: 4096
  persistent_disk: 2048
  instances: 1
  manifest: |
    containers:
    - name: test-ubuntu-docker
      image: ubuntu # should match the docker image name
      command: "--dir /var/lib/test --appendonly yes"
      bind_ports:
      - "9200:9200"
      bind_volumes:
      - "/var/lib/test"
      env-vars:
      - test-key1: testValue1
      - test-key2: testValue2
      # Add custom properties below 
      - custom-variable-name: (( .properties.customer_name.value ))
      - custom-variable-city: (( .properties.city.value ))

```

If there are any custom properties that need to be passed as env variable to the docker image, specify those under the env-vars entry of the manifest. If the properties are dynamic and specified by user input, use the `((.properties.<propName>.value ))` syntax to propagate the value from custom forms to the manifest.

Also, specify the bind_ports and bind_volumes to expose ports and mount volumes from the VM.
