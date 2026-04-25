"""
Setup configuration for Trading Data Agent portfolio project.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="trading-data-agent",
    version="0.1.0",
    author="Rosalyn Chen",
    author_email="xiaoqingwala@gmail.com",
    description="Multi-agent AI system for trading data ingestion, quality assurance, and analysis",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/rosalynchan/trading-data-agent",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=[
        "pandas>=2.1.0",
        "numpy>=1.24.0",
        "pydantic>=2.5.0",
        "pydantic-settings>=2.1.0",
        "python-dotenv>=1.0.0",
        "loguru>=0.7.0",
        "langchain>=0.1.0",
        "langgraph>=0.0.40",
        "openai>=1.3.0",
        "plotly>=5.18.0",
        "jinja2>=3.1.0",
        "python-dateutil>=2.8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)