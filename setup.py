from setuptools import setup, find_packages

setup(
    name='wdnas_client',
    version='0.5',
    packages=find_packages(),
    install_requires=[
        'requests>=2.32.3'
    ]
)