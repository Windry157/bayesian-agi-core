#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bayesian-AGI-Core Python SDK Setup
"""

from setuptools import setup, find_packages

setup(
    name="bayesian-agi",
    version="1.0.0",
    description="Bayesian-AGI-Core Python SDK",
    long_description="""Bayesian-AGI-Core Python SDK

A Python SDK for interacting with the Bayesian-AGI-Core API.
""",
    long_description_content_type="text/markdown",
    author="Bayesian-AGI-Core Team",
    author_email="team@bayesian-agi-core.com",
    url="https://github.com/bayesian-agi-core/bayesian-agi-core",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.27.0"
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
    ],
    python_requires=">=3.10",
)