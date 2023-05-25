import setuptools

setuptools.setup(
    name="pulumi_openttd",
    version="1.0.0",
    author="OpenTTD Dev Team",
    author_email="info@openttd.org",
    description="Pulumi shortcuts used by OpenTTD",
    url="https://github.com/OpenTTD/infra",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[],
)
