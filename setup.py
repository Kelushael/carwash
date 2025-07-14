from setuptools import setup

setup(
    name="carwash",
    version="0.1.0",
    py_modules=["mixer"],
    install_requires=[
        "Flask==2.3.3",
        "click==8.1.7",
        "pydub==0.25.1",
        "pyloudnorm==0.1.1",
        "openai==1.3.8",
        "gunicorn==21.2.0",
        "redis==5.0.1",
        "Flask-Compress==1.14",
    ],
    entry_points={
        "console_scripts": [
            "wash-mix = mixer:cli",
        ],
    },
)
