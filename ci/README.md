The tile-gen pipeline is configured (`fly sp -c ci/pipeline.yml -l ../pipeline-creds/tile-generator.yml 
-p tile-generator -t main`) to use the `pipeline.yml` that is generated when one runs the 
`generate_pipeline_yml.py` python script. Any changes to the pipeline should be made in the pipeline
template file `pipeline.yml.jinja2`
