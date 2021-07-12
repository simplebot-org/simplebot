"""Setup SimpleBot installation."""

import setuptools  # type: ignore


def load_requirements(path: str) -> list:
    """Load requirements from the given relative path."""
    with open(path, encoding="utf-8") as file:
        return [
            line.replace("==", ">=")
            for line in file.read().split("\n")
            if line and not line.startswith(("#", "-"))
        ]


if __name__ == "__main__":
    with open("README.md") as f:
        long_desc = f.read()

    setuptools.setup(
        name="simplebot",
        setup_requires=["setuptools_scm"],
        use_scm_version={
            "root": ".",
            "relative_to": __file__,
            "tag_regex": r"^(?P<prefix>v)?(?P<version>[^\+]+)(?P<suffix>.*)?$",
            "git_describe_command": "git describe --dirty --tags --long --match v*.*.*",
        },
        description="SimpleBot: Extensible bot for Delta Chat",
        long_description=long_desc,
        long_description_content_type="text/markdown",
        author="The SimpleBot Contributors",
        author_email="adbenitez@nauta.cu, holger@merlinux.eu",
        url="https://github.com/simplebot-org/simplebot",
        package_dir={"": "src"},
        packages=setuptools.find_packages("src"),
        keywords="deltachat bot email",
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
        dependency_links=["https://m.devpi.net/dc/master"],
        install_requires=load_requirements("requirements.txt"),
        extras_require={"test": load_requirements("requirements-test.txt")},
        include_package_data=True,
        zip_safe=False,
    )
