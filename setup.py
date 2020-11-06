from setuptools import setup

with open('./README.md') as fp:
    description = fp.read()

setup(
    name='nibble auth service',
    version='0.1',
    description=description,
    author='Edouard Theron',
    author_email='edouard@nibble.ai',
    packages=['nibble_auth_service'],
    zip_safe=False
)
