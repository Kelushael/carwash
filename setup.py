from setuptools import setup

setup(
    name="carwash",
    version="0.1.0",
    py_modules=["mixer"],
    install_requires=[
        "Flask",
        "click",
        "pydub",
        "librosa",
        "pyloudnorm",
        "openai",
    ],
    entry_points={
        "console_scripts": [
            "wash-mix = mixer:cli",
        ],
    },
)
