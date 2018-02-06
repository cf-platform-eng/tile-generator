import unittest
from . import helm

class TestImageFinder(unittest.TestCase):

    def test_finds_top_level_image(self):
        values = {
            'image': 'foo/bar',
            'tag': 1.2
        }
        images = helm.find_required_images(values)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0], "foo/bar:1.2")

    def test_finds_top_level_image_uppercase(self):
        values = {
            'Image': 'foo/bar',
            'Tag': 1.2
        }
        images = helm.find_required_images(values)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0], "foo/bar:1.2")

    def test_finds_top_level_image_using_repository(self):
        values = {
            'repository': 'foo/bar',
            'tag': 1.2
        }
        images = helm.find_required_images(values)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0], "foo/bar:1.2")

    def test_finds_top_level_image_using_imagetag(self):
        values = {
            'image': 'foo/bar',
            'imagetag': 1.2
        }
        images = helm.find_required_images(values)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0], "foo/bar:1.2")

    def test_finds_nested_image(self):
        values = {
            'level1': {
                'level2': {
                    'image': 'foo/bar',
                    'tag': 1.2
                }
            }
        }
        images = helm.find_required_images(values)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0], "foo/bar:1.2")

    def test_finds_nested_image_uppercase(self):
        values = {
            'level1': {
                'level2': {
                    'Image': 'foo/bar',
                    'Tag': 1.2
                }
            }
        }
        images = helm.find_required_images(values)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0], "foo/bar:1.2")

    def test_finds_nested_image_using_repository(self):
        values = {
            'level1': {
                'level2': {
                    'repository': 'foo/bar',
                    'tag': 1.2
                }
            }
        }
        images = helm.find_required_images(values)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0], "foo/bar:1.2")

    def test_finds_nested_image_using_imagetag(self):
        values = {
            'level1': {
                'level2': {
                    'image': 'foo/bar',
                    'imagetag': 1.2
                }
            }
        }
        images = helm.find_required_images(values)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0], "foo/bar:1.2")

    def test_finds_nested_image_using_imagetag(self):
        values = {
            'level1': {
                'level2': {
                    'image': 'foo/bar',
                    'imagetag': 1.2
                }
            }
        }
        images = helm.find_required_images(values)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0], "foo/bar:1.2")

    def test_finds_nested_image_in_image(self): # Case found in fluent-bit helm chart
        values = {
            'image': {
                'image': 'foo/bar',
                'imagetag': 1.2
            }
        }
        images = helm.find_required_images(values)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0], "foo/bar:1.2")

    def test_handles_empty_values(self): # Case found in weave-cloud helm chart
        values = None
        images = helm.find_required_images(values)
        self.assertEqual(len(images), 0)

    def test_handles_tag_only(self): # Case found in anchore helm chart
        values = {
            'image': {
                'tag': 'foo/bar:1.2'
            }
        }
        images = helm.find_required_images(values)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0], "foo/bar:1.2")
