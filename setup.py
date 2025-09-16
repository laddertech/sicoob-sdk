from setuptools import find_packages, setup

setup(
    name='sicoob-sdk',
    version='0.1.23',
    description='SDK Python para integração com a API do Banco Sicoob',
    long_description=open('README.md', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    author='Fábio Thomaz',
    author_email='fabio@ladder.dev.br',
    packages=find_packages(),
    install_requires=[
        'requests>=2.25.1',
        'python-dotenv>=0.15.0',
        'requests-pkcs12>=1.25',
        'pypix-api==0.7.0',
    ],
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-mock>=3.6.1',
            'build>=1.2.2.post1',
            'twine>=6.1.0',
            'ruff>=0.4.2',
        ],
    },
    python_requires='>=3.10',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
)
