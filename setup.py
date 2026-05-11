from setuptools import setup, find_packages

setup(
    name="vhostfactory",
    version="1.0.0",
    description="Automatic Nginx + SSL setup daemon for Ubuntu servers",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        "watchdog==3.0.0",
        "Jinja2==3.1.2",
        "PyYAML==6.0",
    ],
    entry_points={
        "console_scripts": [
            "vhostfactory=vhostfactory.main:main",
        ],
    },
    include_package_data=True,
)
