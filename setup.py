from setuptools import find_packages, setup

setup(
    name='django-raster',
    version='0.3',
    url='https://github.com/geodesign/django-raster',
    author='Daniel Wiesmann',
    author_email='daniel@urbmet.com',
    description='Raster file implementation for Django based on PostGis',
    license='BSD',
    packages=find_packages(exclude=('tests', )),
    include_package_data=True,
    install_requires=[
        'Django>=1.9',
        'numpy>=1.9.1',
        'celery>=3.1.19',
        'Pillow>=2.7.0',
        'django-colorful>=1.0.1',
        'pyparsing>=2.1.8',
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
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Scientific/Engineering :: GIS',
    ]
)
