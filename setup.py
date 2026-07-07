from setuptools import setup, find_packages

setup(
    name="drama-cli",
    version="1.0.0",
    description="AI 短剧自动生成 CLI 工具",
    packages=find_packages(),
    install_requires=[
        "typer>=0.12.0",
        "rich>=13.0.0",
        "openai>=1.0.0",
        "edge-tts>=6.1.0",
        "pillow>=10.0.0",
    ],
    entry_points={
        "console_scripts": [
            "drama=drama_cli.main:main",
        ],
    },
    python_requires=">=3.10",
)