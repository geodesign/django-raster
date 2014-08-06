import os
from setuptools import setup

README = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read()

# Allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-raster',
    version='0.1.0',
    packages=['raster', 'raster.migrations'],
    include_package_data=True,
    license='BSD',
    description='Simple raster file implementation for Django based on PostGis',
    long_description=README,
    url='https://github.com/yellowcap/django-raster',
    author='Daniel Wiesmann',
    author_email='daniel@urbmet.com',
    requires=[
        'python (>= 2.7)',
        'django (>= 1.6)',
        'psycopg2 (>=2.5.3)',
        'South (>=1.0)'
    ],
    zip_safe=False,
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ]
)
