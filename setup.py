from codecs import open
from os import path

from setuptools import find_packages, setup

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='django-raster',
    version='0.7',
    url='https://github.com/geodesign/django-raster',
    author='Daniel Wiesmann',
    author_email='daniel@wiesmann.pt',
    description='Raster file implementation for Django based on PostGis',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    license='BSD',
    packages=find_packages(exclude=('tests', )),
    include_package_data=True,
    install_requires=[
        'Django>=2.0',
        'numpy>=1.14.2',
        'celery>=4.1.0',
        'Pillow>=5.1.0',
        'django-colorful>=1.2',
        'pyparsing>=2.2.0',
        'boto3>=1.7.9',
    ],
    keywords=['django', 'raster', 'gis', 'gdal', 'celery', 'geo', 'spatial'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Framework :: Django',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Scientific/Engineering :: GIS',
    ]
)
