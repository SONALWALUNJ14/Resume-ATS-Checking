import streamlit as st
from google import genai
from pypdf import PdfReader
import json
import re


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="ATS Resume Checker",
    page_icon="📄",
    layout="wide"
)


# ============================================================
# API KEY
# ============================================================

def get_api_key():
    """
    Get Gemini API key from Streamlit Secrets.
    """

    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass

    return None


api_key = get_api_key()


# ============================================================
# GEMINI CLIENT
# ============================================================

@st.cache_resource
def create_client(api_key):
    return genai.Client(api_key=api_key)


# ============================================================
# GET AVAILABLE GEMINI MODELS
# ============================================================

@st.cache_data(ttl=3600)
def get_available_models(api_key):

    try:

        client = create_client(api_key)

        models = []

        for model in client.models.list():

            model_name = model.name

            # Remove "models/" prefix if present
            if model_name.startswith("models/"):
                model_name = model_name.replace("models/", "", 1)

            # Keep models that support text generation
            # based on available metadata
            models.append(model_name)

        return sorted(set(models))

    except Exception as e:

        st.error(f"Could not retrieve Gemini models: {e}")

        return []


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Settings")

    if not api_key:

        api_key = st.text_input(
            "Enter your Google Gemini API key",
            type="password",
            help="Get your API key from Google AI Studio."
        )

    else:

        st.success("API key loaded from Streamlit Secrets ✅")


    # --------------------------------------------------------
    # MODEL DROPDOWN
    # --------------------------------------------------------

    if api_key:

        available_models = get_available_models(api_key)

        if available_models:

            model_name = st.selectbox(
                "Gemini model",
                available_models,
                index=0,
                help="Models currently available to your Gemini API key."
            )

        else:

            model_name = None

            st.warning(
                "No Gemini models were found for this API key."
            )

    else:

        model_name = None


    st.markdown("---")

    st.caption(
        "Your resume text and job description are sent directly "
        "to Google's Gemini API for analysis. Nothing is stored "
        "by this app."
    )


# ============================================================
# PDF TEXT EXTRACTION
# ============================================================

def extract_text_from_pdf(uploaded_file):

    """
    Extract text from uploaded PDF.
    """

    reader = PdfReader(uploaded_file)

    text = ""

    for page in reader.pages:

        page_text = page.extract_text() or ""

        text += page_text + "\n"

    return text.strip()


# ============================================================
# PROMPT
# ============================================================

PROMPT_TEMPLATE = """
You are an expert ATS (Applicant Tracking System) and senior
technical recruiter with deep knowledge of hiring across
software engineering, data, analytics, AI/ML, product and
business roles.

Compare the RESUME against the JOB DESCRIPTION.

Evaluate:

1. Skills
2. Technical keywords
3. Domain experience
4. Years of experience
5. Responsibilities
6. Education
7. Tools and technologies
8. Overall ATS compatibility

Return ONLY valid JSON.

Use exactly this schema:

{{
  "match_percentage": <integer 0-100>,
  "summary": "<2-3 sentence overall verdict>",
  "matching_keywords": [
      "<keyword found in both resume and JD>"
  ],
  "missing_keywords": [
      "<important JD keyword or skill missing from resume>"
  ],
  "strengths": [
      "<specific strength of resume for this JD>"
  ],
  "gaps": [
      "<specific gap relative to JD>"
  ],
  "improvement_suggestions": [
      "<specific actionable resume improvement>"
  ]
}}

Rules:

- match_percentage must be an integer from 0 to 100.
- Evaluate actual alignment, not just keyword frequency.
- Do not inflate the score.
- Identify important missing technical skills.
- Identify missing responsibilities where applicable.
- Reference actual terms from the JD and resume.
- Keep each list item under 20 words.
- Do not invent experience that is not present in the resume.
- Output ONLY the JSON object.
- Do NOT use markdown.
- Do NOT use ```json.

JOB DESCRIPTION:

"""
{job_description}
"""

RESUME:

"""
{resume_text}
"""
"""


# ============================================================
# CLEAN JSON
# ============================================================

def clean_json_response(raw_text):

    text = raw_text.strip()

    # Remove markdown code fences if Gemini adds them
    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"^```\s*",
        "",
        text
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    text = text.strip()

    return json.loads(text)


# ============================================================
# ANALYZE RESUME
# ============================================================

def analyze_resume(
    job_description,
    resume_text,
    api_key,
    model_name
):

    client = create_client(api_key)

    prompt = PROMPT_TEMPLATE.format(
        job_description=job_description,
        resume_text=resume_text
    )

    response = client.models.generate_content(
        model=model_name,
        contents=prompt
    )

    if not response.text:

        raise ValueError(
            "Gemini returned an empty response."
        )

    return clean_json_response(response.text)


# ============================================================
# MAIN UI
# ============================================================

st.title("📄 ATS Resume Checker")

st.write(
    "Paste a job description, upload your resume PDF, "
    "and get an AI-powered ATS compatibility analysis."
)


# ============================================================
# INPUTS
# ============================================================

col1, col2 = st.columns(2)


with col1:

    job_description = st.text_area(
        "📋 Job Description",
        height=350,
        placeholder=(
            "Paste the complete job description here..."
        )
    )


with col2:

    uploaded_resume = st.file_uploader(
        "📄 Upload Resume",
        type=["pdf"]
    )

    resume_preview = ""

    if uploaded_resume is not None:

        try:

            resume_preview = extract_text_from_pdf(
                uploaded_resume
            )

            with st.expander(
                "Preview extracted resume text"
            ):

                st.text(
                    resume_preview[:5000]
                    +
                    (
                        "..."
                        if len(resume_preview) > 5000
                        else ""
                    )
                )

        except Exception as e:

            st.error(
                f"Could not read PDF: {e}"
            )


# ============================================================
# ANALYZE BUTTON
# ============================================================

analyze_clicked = st.button(
    "🔍 Analyze Resume",
    type="primary",
    use_container_width=True
)


# ============================================================
# ANALYSIS
# ============================================================

if analyze_clicked:

    if not api_key:

        st.error(
            "Please enter your Gemini API key."
        )

    elif not model_name:

        st.error(
            "Please select an available Gemini model."
        )

    elif not job_description.strip():

        st.error(
            "Please paste a job description."
        )

    elif uploaded_resume is None:

        st.error(
            "Please upload your resume PDF."
        )

    elif not resume_preview.strip():

        st.error(
            "Could not extract text from this PDF. "
            "Try another PDF."
        )

    else:

        with st.spinner(
            f"Analyzing with {model_name}..."
        ):

            try:

                result = analyze_resume(
                    job_description,
                    resume_preview,
                    api_key,
                    model_name
                )

            except json.JSONDecodeError:

                st.error(
                    "Gemini returned an invalid JSON response. "
                    "Please try again."
                )

                result = None

            except Exception as e:

                st.error(
                    f"Error calling Gemini API: {e}"
                )

                result = None


        # ====================================================
        # DISPLAY RESULTS
        # ====================================================

        if result:

            st.markdown("---")

            # ------------------------------------------------
            # SCORE
            # ------------------------------------------------

            score = result.get(
                "match_percentage",
                0
            )

            score = max(
                0,
                min(
                    int(score),
                    100
                )
            )

            st.subheader("📊 ATS Match Score")

            st.progress(
                score / 100
            )

            st.metric(
                "Resume Match",
                f"{score}%"
            )


            # ------------------------------------------------
            # SUMMARY
            # ------------------------------------------------

            st.subheader(
                "📝 Overall Summary"
            )

            st.write(
                result.get(
                    "summary",
                    ""
                )
            )


            # ------------------------------------------------
            # KEYWORDS
            # ------------------------------------------------

            c1, c2 = st.columns(2)


            with c1:

                st.subheader(
                    "✅ Matching Keywords"
                )

                matching_keywords = result.get(
                    "matching_keywords",
                    []
                )

                if matching_keywords:

                    for keyword in matching_keywords:

                        st.markdown(
                            f"- {keyword}"
                        )

                else:

                    st.info(
                        "No matching keywords identified."
                    )


            with c2:

                st.subheader(
                    "❌ Missing Keywords"
                )

                missing_keywords = result.get(
                    "missing_keywords",
                    []
                )

                if missing_keywords:

                    for keyword in missing_keywords:

                        st.markdown(
                            f"- {keyword}"
                        )

                else:

                    st.success(
                        "No major missing keywords identified."
                    )


            # ------------------------------------------------
            # STRENGTHS & GAPS
            # ------------------------------------------------

            c3, c4 = st.columns(2)


            with c3:

                st.subheader(
                    "💪 Strengths"
                )

                strengths = result.get(
                    "strengths",
                    []
                )

                for strength in strengths:

                    st.markdown(
                        f"- {strength}"
                    )


            with c4:

                st.subheader(
                    "⚠️ Gaps"
                )

                gaps = result.get(
                    "gaps",
                    []
                )

                for gap in gaps:

                    st.markdown(
                        f"- {gap}"
                    )


            # ------------------------------------------------
            # SUGGESTIONS
            # ------------------------------------------------

            st.subheader(
                "🛠️ Resume Improvement Suggestions"
            )

            suggestions = result.get(
                "improvement_suggestions",
                []
            )

            for suggestion in suggestions:

                st.markdown(
                    f"- {suggestion}"
                )


            # ------------------------------------------------
            # MODEL USED
            # ------------------------------------------------

            st.markdown("---")

            st.caption(
                f"Analysis generated using Gemini model: "
                f"`{model_name}`"
            )
