import streamlit as st
import google.generativeai as genai
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

    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass

    return None


api_key = get_api_key()


# ============================================================
# GET AVAILABLE GEMINI MODELS
# ============================================================

def get_available_models(api_key):

    try:

        genai.configure(api_key=api_key)

        available_models = []

        for model in genai.list_models():

            # Only show models that support generateContent
            if "generateContent" in model.supported_generation_methods:

                model_name = model.name.replace(
                    "models/",
                    ""
                )

                available_models.append(model_name)

        return sorted(set(available_models))

    except Exception as e:

        st.error(
            f"Could not retrieve Gemini models: {e}"
        )

        return []


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Settings")

    # --------------------------------------------------------
    # API KEY
    # --------------------------------------------------------

    if not api_key:

        api_key = st.text_input(
            "Enter your Google Gemini API key",
            type="password",
            help="Get your API key from Google AI Studio."
        )

    else:

        st.success(
            "API key loaded from secrets ✅"
        )


    # --------------------------------------------------------
    # MODEL SELECTION
    # --------------------------------------------------------

    if api_key:

        available_models = get_available_models(
            api_key
        )

        if available_models:

            model_name = st.selectbox(
                "🤖 Gemini Model",
                available_models,
                index=0,
                help=(
                    "Models available to your "
                    "Gemini API key."
                )
            )

            st.caption(
                f"{len(available_models)} "
                f"model(s) available"
            )

        else:

            model_name = None

            st.warning(
                "No Gemini models supporting "
                "generateContent were found."
            )

    else:

        model_name = None


    st.markdown("---")

    st.caption(
        "Your resume text and job description are sent "
        "directly to Google's Gemini API for analysis. "
        "Nothing is stored by this app."
    )


# ============================================================
# PDF TEXT EXTRACTION
# ============================================================

def extract_text_from_pdf(uploaded_file):

    """Extract text from uploaded PDF."""

    reader = PdfReader(uploaded_file)

    text = ""

    for page in reader.pages:

        page_text = page.extract_text() or ""

        text += page_text + "\n"

    return text.strip()


# ============================================================
# CLEAN GEMINI JSON RESPONSE
# ============================================================

def clean_json_response(raw_text):

    text = raw_text.strip()

    # Remove ```json
    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    # Remove ```
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

    # Try direct JSON parsing
    try:
        return json.loads(text)

    except json.JSONDecodeError:

        # Try extracting JSON object from response
        match = re.search(
            r"\{.*\}",
            text,
            flags=re.DOTALL
        )

        if match:

            return json.loads(
                match.group(0)
            )

        raise


# ============================================================
# ANALYZE RESUME
# ============================================================

def analyze_resume(
    job_description,
    resume_text,
    api_key,
    model_name
):

    # Configure Gemini
    genai.configure(
        api_key=api_key
    )

    # Create selected Gemini model
    model = genai.GenerativeModel(
        model_name
    )

    # --------------------------------------------------------
    # IMPORTANT:
    # Prompt is created INSIDE the function.
    # This prevents the previous NameError.
    # --------------------------------------------------------

    prompt = f"""
You are an expert ATS (Applicant Tracking System) and
senior technical recruiter with deep knowledge of hiring
across software engineering, data analytics, AI/ML,
marketing analytics, product and business roles.

Compare the RESUME against the JOB DESCRIPTION.

Evaluate the resume based on:

1. Skills
2. Technical keywords
3. Domain experience
4. Years of experience
5. Job responsibilities
6. Education
7. Tools and technologies
8. Overall ATS compatibility

Return ONLY a valid JSON object.

Use exactly this structure:

{{
    "match_percentage": 0,
    "summary": "2-3 sentence overall verdict",
    "matching_keywords": [],
    "missing_keywords": [],
    "strengths": [],
    "gaps": [],
    "improvement_suggestions": []
}}

RULES:

- match_percentage must be an integer between 0 and 100.
- Evaluate real alignment, not just keyword frequency.
- Do not artificially inflate the score.
- Identify important missing technical skills.
- Identify important missing responsibilities.
- Reference actual terms from the job description and resume.
- Keep each list item under 20 words.
- Do not invent experience that is not present.
- Do not assume the candidate has a skill that is not shown.
- Output ONLY the JSON object.
- Do NOT use markdown.
- Do NOT use ```json.
- Do NOT include explanations outside the JSON.

JOB DESCRIPTION
================

{job_description}


RESUME
================

{resume_text}
"""

    # --------------------------------------------------------
    # SEND REQUEST TO GEMINI
    # --------------------------------------------------------

    response = model.generate_content(
        prompt
    )

    # --------------------------------------------------------
    # CHECK RESPONSE
    # --------------------------------------------------------

    if not response.text:

        raise ValueError(
            "Gemini returned an empty response."
        )

    # --------------------------------------------------------
    # PARSE JSON
    # --------------------------------------------------------

    return clean_json_response(
        response.text
    )


# ============================================================
# MAIN APPLICATION
# ============================================================

st.title(
    "📄 ATS Resume Checker"
)

st.write(
    "Paste a job description, upload your resume "
    "(PDF), and get an AI-powered ATS-style "
    "match analysis powered by Google Gemini."
)


# ============================================================
# INPUT AREA
# ============================================================

col1, col2 = st.columns(2)


# ============================================================
# JOB DESCRIPTION
# ============================================================

with col1:

    job_description = st.text_area(
        "📋 Job Description",
        height=350,
        placeholder=(
            "Paste the complete job description here..."
        )
    )


# ============================================================
# RESUME UPLOAD
# ============================================================

with col2:

    uploaded_resume = st.file_uploader(
        "📄 Upload Resume (PDF)",
        type=["pdf"]
    )

    resume_preview = ""

    if uploaded_resume is not None:

        try:

            resume_preview = extract_text_from_pdf(
                uploaded_resume
            )

            with st.expander(
                "👀 Preview Extracted Resume Text"
            ):

                preview_text = resume_preview[:5000]

                if len(resume_preview) > 5000:

                    preview_text += "..."

                st.text(
                    preview_text
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

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if not api_key:

        st.error(
            "❌ Please enter your Gemini API key "
            "in the sidebar."
        )

    elif not model_name:

        st.error(
            "❌ No Gemini model is available."
        )

    elif not job_description.strip():

        st.error(
            "❌ Please paste a job description."
        )

    elif uploaded_resume is None:

        st.error(
            "❌ Please upload your resume PDF."
        )

    elif not resume_preview.strip():

        st.error(
            "❌ Could not extract text from this PDF. "
            "Try another PDF."
        )

    else:

        # ----------------------------------------------------
        # GEMINI ANALYSIS
        # ----------------------------------------------------

        with st.spinner(
            f"🤖 Analyzing resume using {model_name}..."
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
                    "❌ Gemini returned invalid JSON. "
                    "Please click Analyze again."
                )

                result = None

            except Exception as e:

                st.error(
                    f"❌ Error calling Gemini API: {e}"
                )

                result = None


        # ====================================================
        # DISPLAY RESULTS
        # ====================================================

        if result:

            st.markdown("---")


            # =================================================
            # ATS SCORE
            # =================================================

            score = result.get(
                "match_percentage",
                0
            )

            try:

                score = int(score)

            except:

                score = 0

            score = max(
                0,
                min(
                    score,
                    100
                )
            )

            st.subheader(
                "📊 ATS Match Score"
            )

            st.progress(
                score / 100
            )

            st.metric(
                "Resume Match",
                f"{score}%"
            )


            # =================================================
            # SUMMARY
            # =================================================

            st.subheader(
                "📝 Overall Summary"
            )

            st.write(
                result.get(
                    "summary",
                    "No summary available."
                )
            )


            # =================================================
            # KEYWORDS
            # =================================================

            c1, c2 = st.columns(2)


            # -------------------------------------------------
            # MATCHING KEYWORDS
            # -------------------------------------------------

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
                        "No matching keywords found."
                    )


            # -------------------------------------------------
            # MISSING KEYWORDS
            # -------------------------------------------------

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
                        "No major missing keywords found."
                    )


            # =================================================
            # STRENGTHS & GAPS
            # =================================================

            c3, c4 = st.columns(2)


            # -------------------------------------------------
            # STRENGTHS
            # -------------------------------------------------

            with c3:

                st.subheader(
                    "💪 Strengths"
                )

                strengths = result.get(
                    "strengths",
                    []
                )

                if strengths:

                    for strength in strengths:

                        st.markdown(
                            f"- {strength}"
                        )

                else:

                    st.info(
                        "No strengths identified."
                    )


            # -------------------------------------------------
            # GAPS
            # -------------------------------------------------

            with c4:

                st.subheader(
                    "⚠️ Gaps"
                )

                gaps = result.get(
                    "gaps",
                    []
                )

                if gaps:

                    for gap in gaps:

                        st.markdown(
                            f"- {gap}"
                        )

                else:

                    st.info(
                        "No major gaps identified."
                    )


            # =================================================
            # IMPROVEMENT SUGGESTIONS
            # =================================================

            st.subheader(
                "🛠️ Resume Improvement Suggestions"
            )

            suggestions = result.get(
                "improvement_suggestions",
                []
            )

            if suggestions:

                for suggestion in suggestions:

                    st.markdown(
                        f"- {suggestion}"
                    )

            else:

                st.info(
                    "No improvement suggestions returned."
                )


            # =================================================
            # MODEL INFORMATION
            # =================================================

            st.markdown("---")

            st.caption(
                f"🤖 Model used: `{model_name}`"
            )
