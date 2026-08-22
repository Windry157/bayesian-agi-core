#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bayesian-AGI-Core SDK Setup
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="bayesian-agi-sdk",
    version="1.0.0",
    author="Bayesian-AGI-Core Team",
    author_email="dev@bayesian-agi-core.com",
    description="Python SDK for Bayesian-AGI-Core",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/bayesian-agi-core/sdk",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=[
        "requests>=2.31.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "bayesian-agi-cli=bayesian_agi_sdk.cli:main",
        ],
    },
)