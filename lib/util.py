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

import errno
import os
import requests
import shutil
import urllib

class cd:
    """Context manager for changing the current working directory"""
    def __init__(self, newPath, clobber=False):
    	self.clobber = clobber
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        if self.clobber and os.path.isdir(self.newPath):
			shutil.rmtree(self.newPath)
        mkdir_p(self.newPath)
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)

def mkdir_p(dir):
   try:
      os.makedirs(dir)
   except os.error, e:
      if e.errno != errno.EEXIST:
         raise

def download(url, filename):
        urllib.urlretrieve(url, filename)
	# response = requests.get(url, stream=True)
	# with open(filename, 'wb') as file:
	# 	for chunk in response.iter_content(chunk_size=1024):
	# 		if chunk:
	# 			file.write(chunk)

def update_memory(context, manifest):
	memory = manifest.get('memory', '1G')
	unit = memory.lstrip('0123456789').lstrip(' ').lower()
	if unit not in [ 'g', 'gb', 'm', 'mb' ]:
		print >> sys.stderr, 'invalid memory size unit', unit, 'in', memory
		sys.exit(1)
	memory = int(memory[:-len(unit)])
	if unit in [ 'g', 'gb' ]:
		memory *= 1024
	context['total_memory'] += memory
	if memory > context['max_memory']:
		context['max_memory'] = memory
