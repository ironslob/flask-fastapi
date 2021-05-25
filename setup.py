from setuptools import setup

# Metadata goes in setup.cfg. These are here for GitHub's dependency graph.
setup(
    name="Flask-FastAPI",
    install_requires=[
        "Flask >= 1.1.2, < 2.0",
        "Pydantic >= 1.7.3",
        "orjson >= 3.4.6",
        "PyYAML >= 5.4",
    ],
    extras_require={
    },
    #data_files=[
    #    ('flask_fastapi', ['templates/*.html']),
    #],
)
