from setuptools import setup, find_packages

with open('README.md', 'r') as f:
    desc = f.read()

setup(
    name='wdnas_client',
    version='0.6.0',
    packages=find_packages(),
    install_requires=[
        'requests>=2.32.3'
    ],
    long_description=desc,
    long_description_content_type='text/markdown'
)