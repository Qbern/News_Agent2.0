# News Agent 2.0 — Automated Financial Briefing

A Python-based agent that delivers a personalized daily financial news briefing to your inbox every morning. It pulls headlines from four financial media sources, uses Claude AI to curate and summarize the most relevant stories, and adapts to your interests over time through a feedback loop.

---

## What it does

Every morning at 7:30 AM, the agent:

1. Fetches the latest headlines from four RSS feeds across global and regional financial media
2. Sends them to Claude (Anthropic API) with a structured prompt to select and summarize the 8 most relevant stories
3. Formats the output as an HTML email with clickable links and sends it to your inbox
4. Includes a link to a feedback form where you can rate topics by relevance

Every night at 11:00 PM, a second workflow reads your latest feedback from Google Sheets and updates a `preferencias.json` file in the repository. The next morning, the agent incorporates those preferences into its prompt — prioritizing topics you care about and avoiding ones you don't.

---

## News sources

| Source | Coverage | Language |
|--------|----------|----------|
| Reuters Business (via Google News) | Global markets | English |
| Yahoo Finance | US & global markets | English |
| Expansión México | Latin America | Spanish |
| Investing España | European markets | Spanish |

> **Note:** Reuters discontinued its official RSS feeds in March 2026. This agent uses a Google News query filtered to reuters.com as a reliable alternative.

---

## Architecture

```
07:30 AM  cron-job.org triggers GitHub Actions
          → daily_news.yml
            ├── Fetches 5 headlines per source (20 total)
            ├── Loads preferences from preferencias.json
            ├── Calls Claude Haiku with curated prompt
            └── Sends HTML email via Gmail SMTP

11:00 PM  GitHub Actions schedule
          → actualizar_preferencias.yml
            ├── Reads latest Google Form response via Sheets API
            ├── Maps topic ratings to numeric scores
            ├── Overwrites preferencias.json with latest preferences
            └── Commits and pushes changes to the repository
```

---

## Personalization system

After each briefing, users can fill out a short Google Form rating 14 financial topics on a 5-point scale (Not Relevant → Very Relevant), add free-text topics of interest, and rate the overall briefing quality.

The feedback is stored in `preferencias.json` with numeric scores:

```json
{
  "temas": {
    "stock markets (equities)": 3,
    "geopolitics and the global economy": 3,
    "central banks and monetary policy": 2,
    "cryptocurrencies": -1
  },
  "temas_especificos": "Equity, Banxico, EUR/MXN",
  "relevancia_general": 4
}
```

The agent uses this to instruct Claude which topics to prioritize and which to avoid. The system always uses the most recent response — it does not accumulate history, so preferences stay current.

---

## Tech stack

| Component | Tool |
|-----------|------|
| Language | Python 3.14 |
| AI model | Claude Haiku (Anthropic API) |
| RSS parsing | feedparser |
| Email delivery | smtplib + Gmail SMTP |
| Feedback capture | Google Forms + Google Sheets API |
| Scheduling | cron-job.org → GitHub Actions |
| Secret management | GitHub Secrets + python-dotenv |

---

## Project structure

```
News_Agent2.0/
├── agente_news.py               # Main pipeline: fetch → analyze → send
├── actualizar_preferencias.py   # Reads Google Sheets and updates preferences
├── preferencias.json            # Latest user preferences (auto-updated nightly)
├── ultimo_proceso.json          # Tracks last processed form response
├── .github/
│   └── workflows/
│       ├── daily_news.yml               # Morning briefing workflow
│       └── actualizar_preferencias.yml  # Nightly preferences update
└── data/
    ├── raw/
    └── processed/
```

---

## Setup

To run your own instance:

1. Clone the repository
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate      # Windows
   pip install feedparser anthropic python-dotenv gspread google-auth
   ```
3. Create a `.env` file with the following variables:
   ```
   ANTHROPIC_API_KEY=your_key
   GMAIL_USER=your_email@gmail.com
   GMAIL_APP_PASSWORD=your_app_password
   GOOGLE_FORM_URL=your_form_link
   ```
4. Add a `google_credentials.json` file from a Google Cloud service account with Sheets and Drive read access
5. Add the same variables as GitHub Secrets for the Actions workflows
6. Set up a [cron-job.org](https://cron-job.org) trigger pointing to the `daily_news.yml` workflow dispatch endpoint

> **Security note:** `google_credentials.json` and `.env` are excluded via `.gitignore`. All secrets are injected at runtime through GitHub Secrets — nothing sensitive is stored in the repository.

---

## Why cron-job.org instead of GitHub Actions schedule?

GitHub Actions' built-in cron scheduler can delay jobs by 3–15 hours on free-tier private repositories during peak load. Using cron-job.org as an external trigger via the GitHub API dispatch endpoint ensures the briefing arrives at a consistent time every morning.

---

## Background

Built as part of a personal project to combine finance domain knowledge with Python and AI tooling. The goal is to stay informed on global markets through a daily briefing that adapts to evolving interests — without relying on algorithmic feeds or social media.

Part of a broader learning track that includes portfolio analytics, risk-return metrics, and quantitative finance methods.
