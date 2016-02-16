#!/usr/bin/env python

import os
import json

from flask import Flask
app = Flask(__name__)

vcap_application = json.loads(os.getenv('VCAP_APPLICATION','{ "name": "none", "application_uris": [ "http://localhost:8080" ] }'))
host = vcap_application['application_uris'][0]
name = vcap_application['name'].rstrip('01234567889.').rstrip('-')

def route(url):
	return host + url

catalog = {
	"services": [{
		"id": name + '-id',
		"name": name + '-service',
		"description": "A generated test service",
		"bindable": True,
		"plans": [{
			"id": name + '-plan-1-id',
			"name": "first-plan",
			"description": "A first, free, service plan"
		},{
			"id": name + '-plan-2-id',
			"name": "second-plan",
			"description": "A second, for-a-fee, service plan",
			"free": False
		}],
		"dashboard_client": {
			"id": name + '-client-id',
			"secret": "secret",
			"redirect_uri": route('/dashboard')
		}
	}]
}

@app.route("/hello")
def hello():
	return 'hello'

@app.route("/env")
def environment():
	return json.dumps(dict(os.environ), indent=4)

@app.route("/v2/catalog")
def broker_catalog():
	return json.dumps(catalog, indent=4)

@app.route("/v2/service_instances/<instance_id>", methods=['PUT'])
def broker_provision_instance(instance_id):
	return json.dumps({ 'dashboard_url': route('/dashboard/' + instance_id) }, indent=4), 201

@app.route("/v2/service_instances/<instance_id>", methods=['DELETE'])
def broker_deprovision_instance(instance_id):
	return json.dumps({}, indent=4), 200

@app.route("/v2/service_instances/<instance_id>/service_bindings/<binding_id>", methods=['PUT'])
def broker_bind_instance(instance_id, binding_id):
	return json.dumps({ 'credentials': { 'uri': route('/service/' + instance_id) }}, indent=4), 201

@app.route("/v2/service_instances/<instance_id>/service_bindings/<binding_id>", methods=['DELETE'])
def broker_unbind_instance(instance_id, binding_id):
	return json.dumps({}, indent=4), 200

@app.errorhandler(500)
def internal_error(error):
	print error
	return "Internal server error", 500

if __name__ == "__main__":
	app.run(host='0.0.0.0', port=int(os.getenv('PORT', '8080')))
