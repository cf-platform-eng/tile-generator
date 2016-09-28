from setuptools import setup
setup(
    name = "tile_generator",
    version = "0.9.1",
    packages = [ 'tile_generator' ],
    install_requires = [
        'click>=6.2',
        'Jinja2>=2.8',
        'PyYAML>=3.1',
        'docker-py>=1.6.0',
        'requests>=2.9.1',
        'mock>=2.0.0',
    ],
    include_package_data = True,
    entry_points = {
        'console_scripts': [
            'tile = tile_generator.tile:cli',
            'pcf = tile_generator.pcf:cli',
        ]
    }
)
