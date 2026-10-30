from setuptools import setup, find_packages

setup(
    name="vde-vlm",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "Pillow>=9.0.0",
    ],
    extras_require={
        "windows": ["pywin32>=300"],
    },
    entry_points={
        "console_scripts": [
            "vde-vlm=vde_vlm.cli:main",
        ],
    },
)
