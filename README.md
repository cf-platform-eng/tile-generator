# PCF Tile Generator

PCF Tile Generator is a suite of tools to help you develop, package, test,
and deploy services and other add-ons to Pivotal Cloud Foundry. The tile generator
uses templates and patterns that are based on years of experience integrating
third-party services into Cloud Foundry, and eliminates much of the need for
you to have intimate knowledge of all the tools involved.

- Documentation: [Github Pages](http://cf-platform-eng.github.io/isv-portal/tile-generator)
- ISV Portal: [Github Pages](http://cf-platform-eng.github.io/isv-portal)
- Roadmap: [Github Issues](https://github.com/cf-platform-eng/tile-generator/issues)
- CI Pipeline: [Concourse](http://ci.run-01.haas-26.pez.pivotal.io/pipelines/tile-generator)

## Continuous Integration

The master branch of this repository is being monitored by
[this Concourse pipeline](http://ci.run-01.haas-26.pez.pivotal.io/pipelines/tile-generator).
The pipeline verifies that:

- The tile generator passes all unit tests in `tile_generator/*_unittest.py`
- The tile generator successfully builds the sample tile in `sample`
- The generated tile passes all acceptance tests in `ci/acceptance-tests`
- The generated tile successfully deploys to a current version of PCF
- The deployed tile passes all deployment tests in `ci/deployment-tests`

## Contributing to the Tile Generator

We welcome comments, questions, and contributions from community members. Please consider
the following ways to contribute:

- File Github issues for questions, bugs and new features and comment and vote on the ones that you are interested in.
- If you want to contribute code, please make your code changes on a fork of this repository and submit a
pull request to the master branch of tile-generator. We strongly suggest that you first file an issue to
let us know of your intent, or comment on the issue you are planning to address.
