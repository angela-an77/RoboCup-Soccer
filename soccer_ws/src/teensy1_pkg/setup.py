from setuptools import find_packages, setup

package_name = 'teensy1_pkg'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Angela An',
    maintainer_email='angela.jiaren.an@gmail.com',
    description='Teensy1 package',
    license='Apache License 2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'strategist = strategy_pkg.strategist:main',
            'teensy1_bridge_node = teensy1_pkg.teensy1_bridge:main'
        ],
    },
)