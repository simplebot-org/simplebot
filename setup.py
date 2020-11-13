# -*- coding: utf-8 -*-
import setuptools


if __name__ == "__main__":
    with open('README.rst') as f:
        long_desc = f.read()

    setuptools.setup(
        name='simplebot',
        description='SimpleBot: Extensible bot for Delta Chat',
        setup_requires=['setuptools_scm'],
        use_scm_version=True,
        long_description=long_desc,
        long_description_content_type='text/x-rst',
        author='The SimpleBot Contributors',
        author_email='adbenitez@nauta.cu, holger@merlinux.eu',
        url='https://github.com/SimpleBot-Inc/simplebot',
        package_dir={'': 'src'},
        packages=setuptools.find_packages('src'),
        classifiers=['Development Status :: 4 - Beta',
                     'Intended Audience :: Users',
                     'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
                     'Operating System :: POSIX',
                     'Operating System :: MacOS :: MacOS X',
                     'Topic :: Utilities',
                     'Programming Language :: Python :: 3'],
        entry_points='''
            [console_scripts]
            simplebot=deltabot.main:main
            [pytest11]
            deltabot.pytestplugin=deltabot.pytestplugin
        ''',
        python_requires='>=3.5',
        install_requires=['deltachat>=1.40.2.dev', 'py'],
        include_package_data=True,
        zip_safe=False,
    )
