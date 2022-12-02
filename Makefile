ci/pipeline.yml: ci/generate_pipeline_yml.py ci/pipeline.yml.jinja2
	cd ci; python generate_pipeline_yml.py

.PHONY: set-pipeline
set-pipeline: ci/pipeline.yml
	fly set-pipeline -t ppe-isv -p tile-generator -c ci/pipeline.yml
