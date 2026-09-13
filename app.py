import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import json
import re

# ---------- Page config ----------
st.set_page_config(page_title="ATS Resume Checker", page_icon="📄", layout="wide")

# ---------- API Key setup ----------
def get_api_key():
    # 1) Try Streamlit secrets (used in deployed app)
    if "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"]
    return None

api_key = get_api_key()

with st.sidebar:
    st.header("⚙️ Settings")
    if not api_key:
        api_key = st.text_input(
            "Enter your Google Gemini API key",
            type="password",
            help="Get a free key at https://aistudio.google.com/app/apikey",
        )
    else:
        st.success("API key loaded from secrets ✅")

    model_name = st.selectbox(
        "Gemini model",
        ["gemini-2.5-flash", "gemini-2.5-pro"],
        index=0,
        help="Flash is faster & has a bigger free quota. Pro gives deeper analysis.",
    )

    st.markdown("---")
    st.caption(
        "Your resume text and the job description are sent directly to Google's "
        "Gemini API to generate the analysis. Nothing is stored by this app."
    )

# ---------- Helpers ----------
def extract_text_from_pdf(uploaded_file) -> str:
    """Extract raw text from an uploaded PDF file."""
    reader = PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text() or ""
        text += page_text + "\n"
    return text.strip()


PROMPT_TEMPLATE = """
You are an expert ATS (Applicant Tracking System) and senior technical recruiter
with deep knowledge of hiring across software engineering, data, and product roles.

Compare the RESUME below against the JOB DESCRIPTION and evaluate how well the
resume matches the job requirements.

Return your answer as **valid JSON only**, with no markdown fences, matching this schema:

{{
  "match_percentage": <integer 0-100>,
  "summary": "<2-3 sentence overall verdict>",
  "matching_keywords": ["<keyword found in both resume and JD>", ...],
  "missing_keywords": ["<important JD keyword/skill missing from resume>", ...],
  "strengths": ["<specific strength of this resume for this JD>", ...],
  "gaps": ["<specific gap or weakness relative to this JD>", ...],
  "improvement_suggestions": ["<concrete, actionable suggestion to improve the resume>", ...]
}}

Rules:
- match_percentage should reflect real alignment (skills, experience level, domain, keywords).
- Be specific and concrete, not generic. Reference actual terms from the JD/resume where possible.
- Keep each list item short (under 20 words).
- Output ONLY the JSON object, nothing else.

JOB DESCRIPTION:
\"\"\"
{job_description}
\"\"\"

RESUME:
\"\"\"
{resume_text}
\"\"\"
"""


def clean_json_response(raw_text: str) -> dict:
    """Strip markdown fences etc. and parse JSON, with a couple of fallbacks."""
    text = raw_text.strip()
    text = re.sub(r"^```json\s*|^```\s*|```$", "", text, flags=re.MULTILINE).strip()
    return json.loads(text)


def analyze_resume(job_description: str, resume_text: str, api_key: str, model_name: str) -> dict:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    prompt = PROMPT_TEMPLATE.format(job_description=job_description, resume_text=resume_text)
    response = model.generate_content(prompt)
    return clean_json_response(response.text)


# ---------- UI ----------
st.title("📄 ATS Resume Checker")
st.write(
    "Paste a job description, upload your resume (PDF), and get an AI-powered "
    "ATS-style match analysis powered by Google Gemini."
)

col1, col2 = st.columns(2)

with col1:
    job_description = st.text_area(
        "Job Description",
        height=300,
        placeholder="Paste the full job description here...",
    )

with col2:
    uploaded_resume = st.file_uploader("Upload Resume (PDF)", type=["pdf"])
    resume_preview = ""
    if uploaded_resume is not None:
        try:
            resume_preview = extract_text_from_pdf(uploaded_resume)
            with st.expander("Preview extracted resume text"):
                st.text(resume_preview[:3000] + ("..." if len(resume_preview) > 3000 else ""))
        except Exception as e:
            st.error(f"Could not read PDF: {e}")

analyze_clicked = st.button("🔍 Analyze Resume", type="primary", use_container_width=True)

if analyze_clicked:
    if not api_key:
        st.error("Please enter your Gemini API key in the sidebar.")
    elif not job_description.strip():
        st.error("Please paste a job description.")
    elif not uploaded_resume:
        st.error("Please upload a resume PDF.")
    elif not resume_preview.strip():
        st.error("Could not extract any text from that PDF. Try a different file.")
    else:
        with st.spinner("Analyzing resume against job description..."):
            try:
                result = analyze_resume(job_description, resume_preview, api_key, model_name)
            except json.JSONDecodeError:
                st.error("Gemini returned a response that wasn't valid JSON. Please try again.")
                result = None
            except Exception as e:
                st.error(f"Error calling Gemini API: {e}")
                result = None

        if result:
            st.markdown("---")
            score = result.get("match_percentage", 0)
            st.subheader("Match Score")
            st.progress(min(max(score, 0), 100) / 100)
            st.metric("ATS Match", f"{score}%")

            st.subheader("Summary")
            st.write(result.get("summary", ""))

            c1, c2 = st.columns(2)
            with c1:
                st.subheader("✅ Matching Keywords")
                for kw in result.get("matching_keywords", []):
                    st.markdown(f"- {kw}")
            with c2:
                st.subheader("❌ Missing Keywords")
                for kw in result.get("missing_keywords", []):
                    st.markdown(f"- {kw}")

            c3, c4 = st.columns(2)
            with c3:
                st.subheader("💪 Strengths")
                for s in result.get("strengths", []):
                    st.markdown(f"- {s}")
            with c4:
                st.subheader("⚠️ Gaps")
                for g in result.get("gaps", []):
                    st.markdown(f"- {g}")

            st.subheader("🛠️ Suggestions to Improve")
            for s in result.get("improvement_suggestions", []):
                st.markdown(f"- {s}")
