from setuptools import setup, find_packages

with open('README.md', 'r') as f:
    desc = f.read()

setup(
    name='wdnas_client',
    version='0.8.3',
    packages=find_packages(),
    install_requires=[
        'aiohttp>=3.12.14'
    ],
    long_description=desc,
    long_description_content_type='text/markdown'
)