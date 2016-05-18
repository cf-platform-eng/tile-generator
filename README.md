# PCF Tile Generator

PCF Tile Generator is a suite of tools to help you develop, package, test,
and deploy services and other add-ons to Pivotal Cloud Foundry. The tile generator
uses templates and patterns that are based on years of experience integrating
third-party services into Cloud Foundry, and eliminates much of the need for
you to have intimate knowledge of all the tools involved.

- Documentation: [Github Pages](http://cf-platform-eng.github.io/isv-portal/tile-generator)
- ISV Portal: [Github Pages](http://cf-platform-eng.github.io/isv-portal)
- Roadmap: [Github Issues](https://github.com/cf-platform-eng/tile-generator/issues)
- CI Pipeline: [Concourse](https://dragon.somegood.org/pipelines/tile-generator)

## Continuous Integration

The master branch of this repository is being monitored by
[this Concourse pipeline](https://dragon.somegood.org/pipelines/tile-generator).
The pipeline verifies that:

- The tile generator passes all unit tests in `lib/*_unittest.py`
- The tile generator successfully builds the sample tile in `sample`
- The generated tile passes all acceptance tests in `ci/acceptance-tests`
- The generated tile successfully deploys to a current version of PCF
- The deployed tile passes all deployment tests in `ci/deployment-tests`
