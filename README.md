# PCF Tile Generator

PCF Tile Generator is a suite of tools to help you develop, package, test,
and deploy services and other add-ons to Pivotal Cloud Foundry. The tile generator
uses templates and patterns that are based on years of experience integrating
third-party services into Cloud Foundry, and eliminates much of the need for
you to have intimate knowledge of all the tools involved.

- Documentation: [Pivotal Documentation](http://docs.pivotal.io/tiledev/tile-generator.html)
- PCF Tile Developers Guide: [Pivotal Documentation](http://docs.pivotal.io/tiledev/index.html)
- Roadmap: [Github Issues](https://github.com/cf-platform-eng/tile-generator/issues)
- CI Pipeline: [TPE Concourse](https://tpe-concourse-rock.acc.broadcom.net/teams/ppe-isv/pipelines/tile-generator/)

## Continuous Integration

GCP project used in CI - **isv-tile-partners**

The master branch of this repository is being monitored by
[this TPE Concourse pipeline](https://tpe-concourse-rock.acc.broadcom.net/teams/ppe-isv/pipelines/tile-generator/).
The pipeline verifies that:

- The tile generator passes all unit tests in `tile_generator/*_unittest.py`
- The tile generator successfully builds the sample tile in `sample`
- The generated tile passes all acceptance tests in `ci/acceptance-tests`
- The generated tile successfully deploys to a current version of PCF
- The deployed tile passes all deployment tests in `ci/deployment-tests`

## Updating pipeline.yml
- After updating the pipeline template file - pipeline.yml.jinja2, please run the below script to generate the pipeline file from inside the ci directory
```
python3 generate_pipeline_yml.py
```  

To target the pipeline run the following command

```
fly login -t <desired_target_name> -c https://tpe-concourse-rock.acc.broadcom.net -n ppe-isv
```

You need to be a member of the ppe-isv team for the above command to work.

## Contributing to the Tile Generator

We welcome comments, questions, and contributions from community members. Please consider
the following ways to contribute:

- File Github issues for questions, bugs and new features and comment and vote on the ones that you are interested in.
- If you want to contribute code, please make your code changes on a fork of this repository and submit a
pull request to the master branch of tile-generator. We strongly suggest that you first file an issue to
let us know of your intent, or comment on the issue you are planning to address.

### Development

For development, it is useful to install the tile-generator package in
*editable* mode. That is, you can install the tile-generator package
in a way that points to your local repository, so that your code
changes are immediately available through the `tile` or `pcf`
commands. To do this, run this command in your tile-generator
repository directory:

```
./install-git-hook.sh
pip install -e .
```

To avoid downloading dependencies on every `tile build`:
1. `cd sample`
2. `mkdir cache`
3. `tile build --cache cache`

To verify if there are any lint issues:
```
python -m tabnanny tile_generator/opsmgr.py
```

Run indiv

Before executing `./scripts/run_local_tests.sh` install virtualenv with `pip install virtualenv`

Then to execute all test using the cache from the project root use: 
`./scripts/run_local_tests.sh withcache`

### Note: Mac Binaries are no longer supported

Tile generator cli no longer releases new Mac binaries. Check the [commit](https://github.com/cf-platform-eng/tile-generator/commit/1e8db6fb25f1c0e499965df0a113818188548d5b) that removed support for Mac support. MacStadium account has been cancelled and we currently don't have a way to test tile generator cli Mac binaries.

