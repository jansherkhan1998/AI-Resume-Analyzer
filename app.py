import streamlit as st
import os
import json
import time
import re

from google import genai
from google.genai import types

from pypdf import PdfReader
from docx import Document


# ==========================================
# PAGE CONFIG
# ==========================================

st.set_page_config(
    page_title="AI Resume Analyzer",
    page_icon="📄",
    layout="wide"
)


# ==========================================
# API KEY
# ==========================================

API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
    st.error("GEMINI_API_KEY is not configured.")
    st.stop()


client = genai.Client(api_key=API_KEY)


# ==========================================
# READ PDF
# ==========================================

def read_pdf(file):

    reader = PdfReader(file)

    text = ""

    for page in reader.pages:
        text += page.extract_text() or ""

    return text


# ==========================================
# READ DOCX
# ==========================================

def read_docx(file):

    document = Document(file)

    text = ""

    for paragraph in document.paragraphs:
        text += paragraph.text + "\n"

    return text


# ==========================================
# EXTRACT RESUME TEXT
# ==========================================

def extract_resume_text(file):

    if file.name.lower().endswith(".pdf"):
        return read_pdf(file)

    elif file.name.lower().endswith(".docx"):
        return read_docx(file)

    return ""


# ==========================================
# FIND AVAILABLE GEMINI MODELS
# ==========================================

def get_available_models():

    preferred_models = [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash"
    ]

    try:

        available = []

        for model in client.models.list():

            name = model.name.replace("models/", "")

            if name in preferred_models:

                if "generateContent" in model.supported_actions:
                    available.append(name)

        # Keep preferred order
        ordered_models = []

        for model in preferred_models:

            if model in available:
                ordered_models.append(model)

        return ordered_models

    except Exception:

        # Fallback list if model listing fails
        return preferred_models


# ==========================================
# ANALYZE RESUME
# ==========================================

def analyze_resume(resume, job_description):

    prompt = f"""
You are an expert ATS resume analyzer.

Compare the resume with the job description.

RESUME:
{resume}

JOB DESCRIPTION:
{job_description}

Analyze:

1. Overall resume quality
2. ATS compatibility
3. Job match
4. Matching skills
5. Missing skills
6. Important ATS keywords
7. Keyword usage
8. Resume problems
9. Formatting problems
10. Resume strengths
11. Experience match
12. Education match
13. Practical recommendations

IMPORTANT:

- Do not invent information.
- Do not claim that the candidate has a skill unless it appears in the resume.
- Treat similar terminology as a possible match.
- Identify important skills from the job description that are not demonstrated in the resume.
- Check grammar, structure, clarity, measurable achievements and ATS compatibility.
- Recommendations must be practical.
- Do not consider protected personal characteristics.
"""


    # ======================================
    # MODELS
    # ======================================

    models = get_available_models()

    if not models:
        models = [
            "gemini-3.8-flash",
            "gemini-3.7-flash",
            "gemini-3.6-flash"
        ]


    last_error = None


    # ======================================
    # TRY EACH MODEL
    # ======================================

    for model in models:

        # Try each model 2 times
        for attempt in range(2):

            try:

                response = client.models.generate_content(

                    model=model,

                    contents=prompt,

                    config=types.GenerateContentConfig(

                        response_mime_type="application/json",

                        temperature=0.2,

                        max_output_tokens=6000
                    )
                )


                result = response.text.strip()


                # Remove accidental markdown
                result = re.sub(
                    r"```json",
                    "",
                    result,
                    flags=re.IGNORECASE
                )

                result = result.replace("```", "")

                result = result.strip()


                data = json.loads(result)


                return data, model


            except Exception as e:

                last_error = e

                error_text = str(e).upper()


                # Temporary server error
                if "503" in error_text or "UNAVAILABLE" in error_text:

                    if attempt == 0:

                        time.sleep(5)

                    else:

                        time.sleep(2)

                    continue


                # Rate limit
                if (
                    "429" in error_text
                    or "RESOURCE_EXHAUSTED" in error_text
                ):

                    time.sleep(5)

                    continue


                # Invalid model
                if (
                    "404" in error_text
                    or "NOT_FOUND" in error_text
                ):

                    break


                # Other error
                break


    raise Exception(
        f"All Gemini models failed.\n\nLast error:\n{last_error}"
    )


# ==========================================
# UI
# ==========================================

st.title("📄 AI Resume Analyzer")

st.write(
    "Upload your resume and paste the job description "
    "to analyze ATS compatibility and job matching."
)


# ==========================================
# INPUT
# ==========================================

col1, col2 = st.columns(2)


with col1:

    st.subheader("📄 Resume")

    resume_file = st.file_uploader(
        "Upload your resume",
        type=["pdf", "docx"]
    )


with col2:

    st.subheader("💼 Job Description")

    job_description = st.text_area(
        "Paste the job description",
        height=300,
        placeholder="Paste the complete job description here..."
    )


# ==========================================
# ANALYZE
# ==========================================

if st.button("🔍 Analyze Resume", type="primary"):

    if resume_file is None:

        st.warning("Please upload a resume.")

        st.stop()


    if not job_description.strip():

        st.warning("Please enter the job description.")

        st.stop()


    with st.spinner(
        "Analyzing resume... The app will automatically retry/fallback if Gemini is temporarily unavailable."
    ):

        try:

            resume_text = extract_resume_text(resume_file)


            if not resume_text.strip():

                st.error(
                    "Could not extract text from the resume."
                )

                st.stop()


            result, used_model = analyze_resume(
                resume_text,
                job_description
            )


            st.session_state["analysis"] = result

            st.session_state["model"] = used_model


        except Exception as e:

            st.error(
                "Gemini is currently unavailable after trying the available models."
            )

            st.warning(
                "Please wait a few minutes and try again."
            )

            with st.expander("Technical details"):

                st.code(str(e))


# ==========================================
# RESULTS
# ==========================================

if "analysis" in st.session_state:

    result = st.session_state["analysis"]

    used_model = st.session_state["model"]


    st.divider()


    st.success(
        f"Analysis completed using `{used_model}`"
    )


    # ======================================
    # SCORES
    # ======================================

    st.header("📊 Scores")


    col1, col2, col3 = st.columns(3)


    with col1:

        st.metric(
            "Overall Resume Score",
            f"{result.get('overall_score', 0)}/100"
        )


    with col2:

        st.metric(
            "ATS Score",
            f"{result.get('ats_score', 0)}/100"
        )


    with col3:

        st.metric(
            "Job Match Score",
            f"{result.get('job_match_score', 0)}/100"
        )


    # ======================================
    # SUMMARY
    # ======================================

    st.header("📝 Summary")

    st.write(
        result.get("summary", "")
    )


    # ======================================
    # STRENGTHS
    # ======================================

    st.header("✅ Resume Strengths")

    strengths = result.get("strengths", [])

    if strengths:

        for item in strengths:

            st.success(item)

    else:

        st.info("No strengths identified.")


    # ======================================
    # MATCHING SKILLS
    # ======================================

    st.header("🟢 Matching Skills")

    matching_skills = result.get(
        "matching_skills",
        []
    )


    if matching_skills:

        cols = st.columns(3)

        for i, skill in enumerate(matching_skills):

            with cols[i % 3]:

                st.success(skill)

    else:

        st.info("No matching skills identified.")


    # ======================================
    # MISSING SKILLS
    # ======================================

    st.header("🔴 Missing Skills")

    missing_skills = result.get(
        "missing_skills",
        []
    )


    if missing_skills:

        cols = st.columns(3)

        for i, skill in enumerate(missing_skills):

            with cols[i % 3]:

                st.error(skill)

    else:

        st.success(
            "No major missing skills identified."
        )


    # ======================================
    # ATS KEYWORDS
    # ======================================

    st.header("🔑 ATS Keywords")

    keywords = result.get(
        "ats_keywords",
        []
    )


    if keywords:

        st.write(
            ", ".join(keywords)
        )

    else:

        st.info("No ATS keywords identified.")


    # ======================================
    # KEYWORD USAGE
    # ======================================

    st.header("🔍 Keyword Usage")

    keyword_usage = result.get(
        "keyword_usage",
        []
    )


    for item in keyword_usage:

        keyword = item.get(
            "keyword",
            ""
        )

        status = item.get(
            "status",
            ""
        )

        suggestion = item.get(
            "suggestion",
            ""
        )


        if status.lower() == "present":

            st.success(
                f"**{keyword}** — Present"
            )

        else:

            st.warning(
                f"**{keyword}** — {status}\n\n"
                f"{suggestion}"
            )


    # ======================================
    # RESUME PROBLEMS
    # ======================================

    st.header("⚠️ Resume Problems")

    problems = result.get(
        "resume_problems",
        []
    )


    for item in problems:

        problem = item.get(
            "problem",
            ""
        )

        severity = item.get(
            "severity",
            "Medium"
        )

        explanation = item.get(
            "explanation",
            ""
        )


        if severity.lower() == "high":

            st.error(
                f"**{problem}**\n\n"
                f"{explanation}"
            )

        elif severity.lower() == "medium":

            st.warning(
                f"**{problem}**\n\n"
                f"{explanation}"
            )

        else:

            st.info(
                f"**{problem}**\n\n"
                f"{explanation}"
            )


    # ======================================
    # FORMATTING
    # ======================================

    st.header("📐 Formatting & ATS Issues")

    formatting = result.get(
        "formatting_issues",
        []
    )


    if formatting:

        for issue in formatting:

            st.warning(issue)

    else:

        st.success(
            "No major formatting problems identified."
        )


    # ======================================
    # EXPERIENCE
    # ======================================

    st.header("💼 Experience Match")

    st.write(
        result.get(
            "experience_match",
            ""
        )
    )


    # ======================================
    # EDUCATION
    # ======================================

    st.header("🎓 Education Match")

    st.write(
        result.get(
            "education_match",
            ""
        )
    )


    # ======================================
    # RECOMMENDATIONS
    # ======================================

    st.header("🚀 Recommendations")

    recommendations = result.get(
        "recommendations",
        []
    )


    for item in recommendations:

        title = item.get(
            "recommendation",
            "Recommendation"
        )

        reason = item.get(
            "reason",
            ""
        )

        example = item.get(
            "example",
            ""
        )


        with st.expander(title):

            st.write(
                f"**Why:** {reason}"
            )

            if example:

                st.write(
                    f"**Example:** {example}"
                )


    # ======================================
    # FINAL ADVICE
    # ======================================

    st.header("💡 Final Advice")

    st.info(
        result.get(
            "final_advice",
            ""
        )
    )


    # ======================================
    # DOWNLOAD
    # ======================================

    report = json.dumps(
        result,
        indent=4,
        ensure_ascii=False
    )


    st.download_button(

        "⬇️ Download Analysis Report",

        data=report,

        file_name="resume_analysis.json",

        mime="application/json"
    )
