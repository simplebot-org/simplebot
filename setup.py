"""Setup SimpleBot installation."""

import os
import re

import setuptools

if __name__ == "__main__":
    with open("README.md") as f:
        long_desc = f.read()

    init_path = os.path.join("src", "simplebot", "__init__.py")
    with open(init_path, encoding="utf-8") as fh:
        version = re.search(r"__version__ = \"(.*?)\"", fh.read(), re.M).group(1)

    with open("requirements.txt", encoding="utf-8") as req:
        install_requires = [
            line.replace("==", ">=")
            for line in req.read().split("\n")
            if line and not line.startswith(("#", "-"))
        ]
    with open("requirements-test.txt", encoding="utf-8") as req:
        test_deps = [
            line.replace("==", ">=")
            for line in req.read().split("\n")
            if line and not line.startswith(("#", "-"))
        ]

    setuptools.setup(
        name="simplebot",
        description="SimpleBot: Extensible bot for Delta Chat",
        version=version,
        long_description=long_desc,
        long_description_content_type="text/markdown",
        author="The SimpleBot Contributors",
        author_email="adbenitez@nauta.cu, holger@merlinux.eu",
        url="https://github.com/simplebot-org/simplebot",
        package_dir={"": "src"},
        packages=setuptools.find_packages("src"),
        classifiers=[
            "Development Status :: 4 - Beta",
            "Intended Audience :: Developers",
            "Intended Audience :: System Administrators",
            "Intended Audience :: End Users/Desktop",
            "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
            "Operating System :: POSIX",
            "Topic :: Utilities",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
        ],
        entry_points="""
            [console_scripts]
            simplebot=simplebot.main:main
            [pytest11]
            simplebot.pytestplugin=simplebot.pytestplugin
        """,
        python_requires=">=3.5",
        install_requires=install_requires,
        extras_require={"test": test_deps},
        include_package_data=True,
        zip_safe=False,
    )
