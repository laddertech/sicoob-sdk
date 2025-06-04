from setuptools import setup, find_packages

setup(
    name="sicoob-sdk",
    version="0.1.0",
    description="SDK Python para integração com a API do Banco Sicoob",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Seu Nome",
    author_email="seu@email.com",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.1",
        "python-dotenv>=0.15.0",
    ],
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
)
