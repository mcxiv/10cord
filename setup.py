import setuptools

install_requires = open('requirements.txt').read().splitlines()

setuptools.setup(
    name="10cord",
    version="1.0",
    packages=setuptools.find_packages(),
    install_requires=install_requires,
    entry_points={
        'console_scripts': [
            '10cord=src.10cord:main',
        ]
    },
    include_package_data=True,
)
