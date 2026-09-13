# 📄 ATS Resume Checker

A Streamlit app that compares a resume (PDF) against a job description using
Google Gemini and returns an ATS-style match score, missing keywords,
strengths, gaps, and improvement suggestions.

## Features
- Paste any job description
- Upload a resume as PDF (text is extracted automatically)
- Sends both to Google Gemini for analysis
- Shows a match %, keyword gaps, strengths, weaknesses, and concrete suggestions

## 1. Run locally

```bash
git clone <your-repo-url>
cd resume-ats-checker
pip install -r requirements.txt
```

Get a free Gemini API key: https://aistudio.google.com/app/apikey

Set it up locally (either works):
- Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and put your key in it, **or**
- Just paste the key into the sidebar text box when the app runs (not saved anywhere).

Run the app:

```bash
streamlit run app.py
```

It opens at http://localhost:8501

## 2. Deploy for free (Streamlit Community Cloud)

1. Push this folder to a **public GitHub repo**.
2. Go to https://share.streamlit.io and sign in with GitHub.
3. Click **"New app"**, pick your repo/branch, and set the main file to `app.py`.
4. Before/after deploying, open **App settings → Secrets** and paste:
   ```toml
   GEMINI_API_KEY = "your-real-key-here"
   ```
5. Click **Deploy**. You'll get a free public URL like
   `https://your-app-name.streamlit.app`.

That's it — no server, no credit card, free hosting.

### Notes
- Streamlit Community Cloud apps sleep after inactivity and wake up on the next
  visit (takes a few seconds) — normal for the free tier.
- Never commit a real `secrets.toml` file to GitHub — it's already in
  `.gitignore`. Use the Cloud dashboard's Secrets manager instead.
- The `gemini-2.5-flash` model has a generous free-tier quota and is the
  default; switch to `gemini-2.5-pro` in the sidebar for deeper analysis if
  you have quota for it.

## Project structure

```
resume-ats-checker/
├── app.py                          # Streamlit app
├── requirements.txt                # Python dependencies
├── .streamlit/
│   └── secrets.toml.example        # Template for API key (copy, don't commit real one)
├── .gitignore
└── README.md
```
