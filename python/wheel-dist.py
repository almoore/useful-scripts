import os
from setuptools import setup
from setuptools.dist import Distribution

class BinaryDistribution(Distribution):
    def is_pure(self):
        return False

setup(
    
    include_package_data=True,
    distclass=BinaryDistribution,
)
