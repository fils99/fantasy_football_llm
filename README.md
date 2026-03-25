# Fanta-AI

A personal Streamlit app that combines Fantacalcio.it statistics with Google Gemini to help decide who to field each matchday. It reads a local Excel file exported from Fantacalcio.it, lets you manage your squad, and calls Gemini (with Google Search grounding) to get up-to-date advice on injuries, fixtures, and optimal lineup.


## What it does

Two main tabs:

**Comparison**: pick two or more players and ask the AI who to start. It checks recent news and the upcoming fixture before giving a verdict.

**Lineup**: define your full 25-man squad by role, then generate an optimal starting 11 with module choice. Optionally enables a "defense modifier" rule for leagues that award bonus points for clean sheets.

## Setup

You need a [Google Gemini API key](https://ai.google.dev/gemini-api/docs/api-key). Set it as an environment variable before running:

```bash
export Gemini_Google_API_Key="your-key-here"
```

Install dependencies with whatever environment manager you prefer, then:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Data

The Excel file containing the statistics is already included in the repo (`data/fanta_stats.xlsx`). It will be automatically loaded by the app.

Your squad is saved locally in `my_fanta_squad.json`, so you can close the app and come back without losing your setup.
