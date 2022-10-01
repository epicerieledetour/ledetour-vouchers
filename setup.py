from setuptools import setup

setup(
    name="ldtvouchers",
    version="0.0.0",
    include_package_data=True,
    packages=["app"],
    scripts=["bin/send_report.sh"],
    python_requires=">=3.7",
    install_requires=["fastapi", "uvicorn[standard]", "Jinja2", "shortuuid"],
)
