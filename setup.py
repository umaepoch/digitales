from setuptools import setup, find_packages
import os

version = '0.0.1'

setup(
    name='digitales',
    version=version,
    description='digitales',
    author='digitales',
    author_email='rohitw1991@gmail.com',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=("frappe",),
)
