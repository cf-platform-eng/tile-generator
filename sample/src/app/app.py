#!/usr/bin/env python

# tile-generator
#
# Copyright (c) 2015-Present Pivotal Software, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import traceback
import json
import requests
import re

from flask import Flask
from flask import request
app = Flask(__name__)

vcap_application = json.loads(os.getenv('VCAP_APPLICATION','{ "name": "none", "application_uris": [ "http://localhost:8080" ] }'))
host = vcap_application['application_uris'][0]
name = re.sub('-[0-9].*\\Z', '', vcap_application['name'])

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
			"redirect_uri": "http://" + route('/dashboard')
		}
	}]
}

@app.route("/hello")
def hello():
	return 'hello'

@app.route("/env")
def environment():
	return json.dumps(dict(os.environ), indent=4)

@app.route("/proxy")
def proxy():
	url = request.args.get('url')
	if url is None:
		return json.dumps('expected url parameter'), 404
	response = requests.get(url, verify=False)
	return response.content, response.status_code

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
	try:
		app.run(host='0.0.0.0', port=int(os.getenv('PORT', '8080')))
		print >>sys.stderr, " * Exited normally"
	except:
		print >>sys.stderr, " * Exited with exception"
		traceback.print_exc()
