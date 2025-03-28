from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="cover_letter_generator",
    version="1.0.3",  # Match with your config.py VERSION
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "gradio",
        "fpdf",
        "PyPDF2",
        "docx2txt",
        "reportlab",
        "gradio_pdf",
        "beautifulsoup4",
        "requests",
        "Crawl4AI==0.4.248",
        "groq",
        "python-dotenv",
    ],
    author="Subhash",
    author_email="subhashbs36@github.com",  # Update with your email
    description="AI-Powered Job Application Assistant",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/subhashbs36/Applicator",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Office/Business",
    ],
    python_requires=">=3.12",
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "applicator=src.app.cover_letter_app:main",
        ],
    },
)