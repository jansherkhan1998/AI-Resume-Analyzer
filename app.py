import streamlit as st
import os
import json
import re
from google import genai
from pypdf import PdfReader
from docx import Document


# -----------------------------
# PAGE CONFIG
# -----------------------------

st.set_page_config(
    page_title="AI Resume Analyzer",
    page_icon="📄",
    layout="wide"
)


# -----------------------------
# GEMINI CLIENT
# -----------------------------

API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
    st.error("GEMINI_API_KEY is not set.")
    st.stop()

client = genai.Client(api_key=API_KEY)


# -----------------------------
# READ PDF
# -----------------------------

def read_pdf(file):
    reader = PdfReader(file)
    text = ""

    for page in reader.pages:
        text += page.extract_text() or ""

    return text


# -----------------------------
# READ DOCX
# -----------------------------

def read_docx(file):
    document = Document(file)
    text = ""

    for paragraph in document.paragraphs:
        text += paragraph.text + "\n"

    return text


# -----------------------------
# READ RESUME
# -----------------------------

def extract_resume_text(file):

    if file.name.lower().endswith(".pdf"):
        return read_pdf(file)

    if file.name.lower().endswith(".docx"):
        return read_docx(file)

    return ""


# -----------------------------
# GEMINI ANALYSIS
# -----------------------------

def analyze_resume(resume, job_description):

    prompt = f"""
You are an expert ATS resume analyzer and career assistant.

Analyze the resume against the provided job description.

RESUME:
{resume}

JOB DESCRIPTION:
{job_description}

Return ONLY valid JSON.

Use exactly this structure:

{{
    "overall_score": 0,
    "ats_score": 0,
    "job_match_score": 0,

    "summary": "",

    "matching_skills": [],

    "missing_skills": [],

    "ats_keywords": [],

    "keyword_usage": [
        {{
            "keyword": "",
            "status": "Present",
            "suggestion": ""
        }}
    ],

    "resume_problems": [
        {{
            "problem": "",
            "severity": "High",
            "explanation": ""
        }}
    ],

    "recommendations": [
        {{
            "recommendation": "",
            "reason": "",
            "example": ""
        }}
    ],

    "strengths": [],

    "formatting_issues": [],

    "experience_match": "",

    "education_match": "",

    "final_advice": ""
}}

Important rules:

1. Scores must be numbers from 0 to 100.
2. Matching skills must contain skills found in both the resume and job description.
3. Missing skills must contain important job requirements that are not demonstrated in the resume.
4. ATS keywords should be important keywords from the job description.
5. Do not invent experience, skills, education, certifications, or achievements.
6. Recommendations should explain how the candidate can improve the resume.
7. If a missing skill is actually present using a different wording, consider it a match.
8. Check grammar, formatting, clarity, measurable achievements, keywords, headings, and ATS compatibility.
9. Keep recommendations practical.
10. Do not discriminate based on age, gender, religion, nationality, race, disability, marital status, or other protected characteristics.
"""


    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    result = response.text

    # Remove markdown JSON formatting if Gemini adds it
    result = re.sub(r"```json", "", result)
    result = re.sub(r"```", "", result)

    result = result.strip()

    return json.loads(result)


# -----------------------------
# HEADER
# -----------------------------

st.title("📄 AI Resume Analyzer")
st.write(
    "Upload your resume and paste the job description to see how well your resume matches the job."
)


# -----------------------------
# INPUTS
# -----------------------------

col1, col2 = st.columns(2)

with col1:

    st.subheader("📄 Resume")

    resume_file = st.file_uploader(
        "Upload Resume",
        type=["pdf", "docx"]
    )

with col2:

    st.subheader("💼 Job Description")

    job_description = st.text_area(
        "Paste the Job Description",
        height=300,
        placeholder="Paste the complete job description here..."
    )


# -----------------------------
# ANALYZE BUTTON
# -----------------------------

if st.button("🔍 Analyze Resume", type="primary"):

    if resume_file is None:
        st.warning("Please upload your resume.")

    elif not job_description.strip():
        st.warning("Please enter the job description.")

    else:

        with st.spinner("AI is analyzing your resume..."):

            try:

                resume_text = extract_resume_text(resume_file)

                if not resume_text.strip():
                    st.error("Could not extract text from the resume.")
                    st.stop()

                result = analyze_resume(
                    resume_text,
                    job_description
                )

                st.session_state["analysis"] = result

            except Exception as e:

                st.error("Something went wrong while analyzing the resume.")

                st.code(str(e))


# -----------------------------
# SHOW RESULTS
# -----------------------------

if "analysis" in st.session_state:

    result = st.session_state["analysis"]

    st.divider()

    st.header("📊 Resume Analysis")

    # -----------------------------
    # SCORES
    # -----------------------------

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Overall Resume Score",
            f"{result['overall_score']}/100"
        )

    with col2:
        st.metric(
            "ATS Score",
            f"{result['ats_score']}/100"
        )

    with col3:
        st.metric(
            "Job Match Score",
            f"{result['job_match_score']}/100"
        )


    # -----------------------------
    # SUMMARY
    # -----------------------------

    st.subheader("📝 Summary")

    st.write(result["summary"])


    # -----------------------------
    # STRENGTHS
    # -----------------------------

    st.subheader("✅ Resume Strengths")

    for item in result["strengths"]:
        st.success(item)


    # -----------------------------
    # MATCHING SKILLS
    # -----------------------------

    st.subheader("🟢 Matching Skills")

    if result["matching_skills"]:

        cols = st.columns(3)

        for i, skill in enumerate(result["matching_skills"]):

            with cols[i % 3]:
                st.success(skill)

    else:
        st.info("No strong matching skills were identified.")


    # -----------------------------
    # MISSING SKILLS
    # -----------------------------

    st.subheader("🔴 Missing Skills")

    if result["missing_skills"]:

        cols = st.columns(3)

        for i, skill in enumerate(result["missing_skills"]):

            with cols[i % 3]:
                st.error(skill)

    else:
        st.success("No major missing skills identified.")


    # -----------------------------
    # ATS KEYWORDS
    # -----------------------------

    st.subheader("🔑 ATS Keywords")

    keywords = result["ats_keywords"]

    if keywords:

        st.write(", ".join(keywords))

    else:
        st.info("No keywords identified.")


    # -----------------------------
    # KEYWORD USAGE
    # -----------------------------

    st.subheader("🔍 Keyword Usage")

    for item in result["keyword_usage"]:

        keyword = item["keyword"]
        status = item["status"]
        suggestion = item["suggestion"]

        if status.lower() == "present":

            st.success(f"**{keyword}** — Present")

        else:

            st.warning(
                f"**{keyword}** — {status}\n\n"
                f"{suggestion}"
            )


    # -----------------------------
    # RESUME PROBLEMS
    # -----------------------------

    st.subheader("⚠️ Resume Problems")

    for item in result["resume_problems"]:

        severity = item["severity"]

        if severity.lower() == "high":

            st.error(
                f"**{item['problem']}**\n\n"
                f"{item['explanation']}"
            )

        elif severity.lower() == "medium":

            st.warning(
                f"**{item['problem']}**\n\n"
                f"{item['explanation']}"
            )

        else:

            st.info(
                f"**{item['problem']}**\n\n"
                f"{item['explanation']}"
            )


    # -----------------------------
    # FORMATTING ISSUES
    # -----------------------------

    st.subheader("📐 Formatting & ATS Issues")

    if result["formatting_issues"]:

        for issue in result["formatting_issues"]:
            st.warning(issue)

    else:

        st.success("No major formatting problems identified.")


    # -----------------------------
    # EXPERIENCE MATCH
    # -----------------------------

    st.subheader("💼 Experience Match")

    st.write(result["experience_match"])


    # -----------------------------
    # EDUCATION MATCH
    # -----------------------------

    st.subheader("🎓 Education Match")

    st.write(result["education_match"])


    # -----------------------------
    # RECOMMENDATIONS
    # -----------------------------

    st.subheader("🚀 Recommendations")

    for item in result["recommendations"]:

        with st.expander(item["recommendation"]):

            st.write(
                f"**Why:** {item['reason']}"
            )

            if item["example"]:

                st.write(
                    f"**Example:** {item['example']}"
                )


    # -----------------------------
    # FINAL ADVICE
    # -----------------------------

    st.subheader("💡 Final Advice")

    st.info(result["final_advice"])


    # -----------------------------
    # DOWNLOAD REPORT
    # -----------------------------

    report = f"""
AI RESUME ANALYZER REPORT

Overall Resume Score: {result['overall_score']}/100
ATS Score: {result['ats_score']}/100
Job Match Score: {result['job_match_score']}/100

SUMMARY
{result['summary']}

MATCHING SKILLS
{', '.join(result['matching_skills'])}

MISSING SKILLS
{', '.join(result['missing_skills'])}

ATS KEYWORDS
{', '.join(result['ats_keywords'])}

STRENGTHS
{chr(10).join('- ' + x for x in result['strengths'])}

FORMATTING ISSUES
{chr(10).join('- ' + x for x in result['formatting_issues'])}

EXPERIENCE MATCH
{result['experience_match']}

EDUCATION MATCH
{result['education_match']}

RESUME PROBLEMS
"""

    for item in result["resume_problems"]:

        report += (
            f"\n- {item['problem']} "
            f"({item['severity']}): "
            f"{item['explanation']}"
        )


    report += "\n\nRECOMMENDATIONS\n"

    for item in result["recommendations"]:

        report += (
            f"\n- {item['recommendation']}\n"
            f"  Why: {item['reason']}\n"
            f"  Example: {item['example']}\n"
        )


    report += f"""

FINAL ADVICE
{result['final_advice']}
"""


    st.download_button(
        label="⬇️ Download Analysis Report",
        data=report,
        file_name="resume_analysis.txt",
        mime="text/plain"
    )
