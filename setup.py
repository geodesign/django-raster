import os

from setuptools import setup

README = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read()

os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-raster',
    version='0.1.7',
    packages=['raster', 'raster.migrations'],
    include_package_data=True,
    license='BSD',
    description='Simple raster file implementation for Django based on PostGis',
    long_description=README,
    url='https://github.com/geodesign/django-raster',
    download_url='https://github.com/geodesign/django-raster/tarball/v0.1.6',
    author='Daniel Wiesmann',
    author_email='daniel@urbmet.com',
    install_requires=[
        'psycopg2>=2.5.3',
        'Django>=1.9',
        'numpy>=1.9.1',
        'Pillow>=2.7.0',
        'django-colorful>=1.0.1',
        'pyparsing>=2.0.3'
    ],
    keywords=['django', 'raster', 'gis', 'gdal', 'celery', 'geo', 'spatial'],
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ]
)
