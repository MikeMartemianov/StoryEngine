from setuptools import setup, find_packages

setup(
    name="story_engine",
    version="1.0",
    packages=find_packages(),
    description="Lib for create stories.",
    author="Mike",
    python_requires=">=3.6",
    install_requires=[
        "kivy>=2.1.0",       # минимальная версия kivy (укажи нужную)
        "kivymd>=1.1.1",     # минимальная версия kivymd (укажи нужную)
    ],
)
