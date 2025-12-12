from setuptools import setup, find_packages

setup(
    name="workflow-generator",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "pytest",
        "hypothesis",
        "sentence-transformers",
        "psycopg2-binary",
        "python-dotenv",
        "coverage",
        "numpy",
        "jsonschema"
    ]
)