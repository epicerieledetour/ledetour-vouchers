from setuptools import find_packages, setup

setup(
    name="ldtvouchers",
    version="0.0.0",
    packages=find_packages(include=["app"]),
    python_requires=">=3.10.0",
    install_requires=[
        "fastapi",
        "uvicorn[standard]",
        "Jinja2",
    ],
)
