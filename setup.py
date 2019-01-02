from setuptools import setup

setup(
    name = 'zendown',
    version = '0.1.0',
    packages = ['zendown'],
    entry_points = {
        'console_scripts': [
            'zendown = zendown.__main__:main'
        ]
    })
