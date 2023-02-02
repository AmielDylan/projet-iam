from setuptools import find_packages, setup

setup(
    name='iam',
    version='1.0.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'flask',
        'mysql-connector-python',
    ],
)