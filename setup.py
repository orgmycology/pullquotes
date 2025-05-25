from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pullquotes",
    version="0.1.0",
    author="OrgMycology",
    author_email="info@orgmycology.com",
    description="A tool for extracting and personalizing quotes from markdown documents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/orgmycology/pullquotes",
    py_modules=["pull_quotes"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    entry_points={
        "console_scripts": [
            "pullquotes=pull_quotes:main",
        ],
    },
)