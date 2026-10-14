# AI Text Summarizer

A Streamlit app that summarizes text, PDF and DOCX files, webpages, and YouTube transcripts using AI.

This is my first prompt engineering project. I built it to learn how prompts can guide AI models to generate summaries in different styles, tones, and languages. While working on it, I also explored Streamlit, document processing, API integration, and building a complete Python application.

## Features

- Summarize pasted text, PDF files, DOCX files, public webpages, and available YouTube transcripts.
- Choose from 12 summary styles, 7 tones, 9 output languages, and 6 target-length options.
- Customize prompts with options for preserving names, numbers, and quotes, removing repetition, and generating titles, keywords, and hashtags.
- Use OpenAI, an optional Hugging Face model, or an extractive summarizer that works offline.
- Process long documents using text chunking.
- View word counts, token estimates, compression ratio, and estimated reading time.
- Download summaries as TXT, Markdown, PDF, or DOCX.
- Summarize multiple PDFs and download the results as a ZIP file.
- Search and delete saved summaries from local history.
- Configure API settings, model parameters, and dark mode.

## Tech Stack

- Python
- Streamlit
- OpenAI API
- Hugging Face Transformers (optional)
- PyPDF
- python-docx
- ReportLab

## Getting Started

### Requirements

Python 3.11 or newer is recommended.

### Installation

Clone the repository and open the project directory:

```powershell
git clone <your-repository-url>
cd <your-project-directory>
```

Create and activate a virtual environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the application:

```powershell
streamlit run app.py
```

Open the local URL shown in the terminal, usually `http://localhost:8501`.

## API Configuration

To use OpenAI, add your API key through the **Settings** page or configure it as an environment variable:

```powershell
$env:OPENAI_API_KEY="your-api-key"
```

You can also use Streamlit secrets for deployment:

```toml
OPENAI_API_KEY = "your-api-key"
```

Without an API key, Automatic mode uses the extractive summarizer. You can also select Extractive mode directly to summarize text offline.

The extractive engine selects sentences from the original text. It does not generate new wording or translate the content.

## Optional: Hugging Face

To use the local summarization model, install the additional dependencies:

```powershell
python -m pip install -r requirements-local-model.txt
```

The model is downloaded on its first run. Local summarization may require additional memory and disk space.

## Project Structure

```text
data/
    history.json
pages/
    Batch_Summarizer.py
    History.py
    Home.py
    Settings.py
test/
    test_summarizer.py
utils/
    doc_reader.py
    export.py
    helpers.py
    pdf_reader.py
    summarizer.py
    tokenizer.py
    web_scraper.py
    youtube_loader.py
app.py
requirements.txt
requirements-local-model.txt
```

## Notes

- PDF and DOCX uploads are limited to 20 MB each.
- PDFs are limited to 2,000 pages.
- Scanned PDFs without selectable text are not supported by the current implementation.
- YouTube summarization requires an available transcript.
- Summary history is stored locally in `data/history.json`.
- Local history may not persist on hosting platforms with ephemeral storage.
- Never commit API keys or files containing secrets to GitHub.

## What I Learned

This project is my starting point in prompt engineering. I experimented with writing instructions that control the style, length, tone, and structure of AI-generated summaries.

I also learned how to connect different components into one application, handle different document formats, work with APIs, and build a user interface using Streamlit.

I'm still learning and plan to keep improving the project as I gain more experience.
