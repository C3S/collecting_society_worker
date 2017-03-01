import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

install_requires = [
    'proteus==3.4.8',
    'click==6.7',
    'pyechonest',
]
test_requires = [
    'coverage',
    'nose',
]
docs_requires = [
    'sphinx==1.5.2',  # for generating the documentation
    'sphinxcontrib-plantuml==0.8.1',
]
setup(
    name='c3sFingerprinting',
    version='0.0',
    description='c3sFingerprinting',
    long_description=README + '\n\n' + CHANGES,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Financial and Insurance Industry',
        'Intended Audience :: Legal Industry',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Programming Language :: Python :: 2.7',
        'Topic :: Office/Business',
    ],
    license='AGPL-3',
    author='Thomas Mielke',
    author_email='thomas.mielke@c3s.cc',
    url='https://github.com/C3S/collecting_society.portal',
    keywords='c3s collecting society fingerprint echoprint tryton',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    test_suite='c3sfingerprinting',
    install_requires=install_requires + docs_requires,
    tests_require=test_requires,
)
