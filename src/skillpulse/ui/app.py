"""Streamlit portfolio experience for SkillPulse AI."""

from __future__ import annotations

import os
from typing import Any

import streamlit as st

from skillpulse.ui.api_client import SkillPulseAPIClient, SkillPulseAPIError
from skillpulse.ui.examples import EXAMPLE_CV, EXAMPLE_EXTRACTION, EXAMPLE_JOB


def _chips(items: list[str], *, empty: str) -> None:
    if not items:
        st.caption(empty)
        return
    st.markdown(" ".join(f"`{item}`" for item in items))


def _render_match(payload: dict[str, Any]) -> None:
    score = float(payload["overall_score"])
    verdict_labels = {
        "strong_match": "Strong match",
        "potential_match": "Potential match",
        "skill_gap": "Skill gap",
    }
    first, second, third = st.columns(3)
    first.metric("Match score", f"{score:.1f}/100")
    second.metric("Verdict", verdict_labels[payload["verdict"]])
    third.metric("Skill gaps", len(payload["missing_skills"]))
    st.progress(score / 100, text="Requirement coverage")

    matched_tab, gaps_tab, evidence_tab = st.tabs(["Matched", "Prioritas belajar", "Evidence"])
    with matched_tab:
        _chips(payload["matched_skills"], empty="Belum ada requirement yang cocok terdeteksi.")
    with gaps_tab:
        _chips(payload["missing_skills"], empty="Tidak ada gap taxonomy yang terdeteksi.")
        for item in payload["learning_priorities"]:
            st.info(f"{item['priority'].upper()} · {item['skill']} — {item['reason']}")
    with evidence_tab:
        rows = [
            {
                "Category": item["category"].replace("_", " ").title(),
                "Score": "N/A" if item["score"] is None else f"{100 * item['score']:.0f}%",
                "Weight": f"{100 * item['effective_weight']:.1f}%",
                "Explanation": item["explanation"],
            }
            for item in payload["category_scores"]
        ]
        st.dataframe(rows, hide_index=True, use_container_width=True)
    st.caption(payload["disclaimer"])


def _render_extraction(payload: dict[str, Any]) -> None:
    for title, field in (
        ("Technical skills", "technical_skills"),
        ("Tools", "tools"),
        ("Soft skills", "soft_skills"),
    ):
        st.markdown(f"**{title}**")
        _chips([item["canonical"] for item in payload[field]], empty="Tidak terdeteksi.")
    first, second, third = st.columns(3)
    first.metric("Experience", payload["experience_years"] if payload["experience_years"] is not None else "Unknown")
    second.metric("Seniority", payload["seniority"].title())
    third.metric("Work mode", payload["work_arrangement"].title())
    st.caption(
        f"Contract {payload['contract_version']} · Taxonomy {payload['taxonomy_version']} · "
        "Klik evidence JSON melalui API docs untuk melihat source spans lengkap."
    )


def render() -> None:
    st.set_page_config(page_title="SkillPulse AI", page_icon="📈", layout="wide")
    st.markdown(
        """
        <style>
        .stApp {background: linear-gradient(145deg, #f6fbff 0%, #f8fafc 48%, #fff7ed 100%);}
        [data-testid="stMetric"] {background:#ffffff;border:1px solid #dbe7f0;padding:16px;border-radius:16px;}
        .hero {padding:1.6rem 1.8rem;border-radius:24px;background:linear-gradient(120deg,#0f172a,#164e63);
               color:white;margin-bottom:1.2rem;box-shadow:0 18px 45px rgba(15,23,42,.16)}
        .hero p {color:#d8f3f6;margin-bottom:0}.eyebrow {font-size:.78rem;letter-spacing:.14em;color:#67e8f9}
        </style>
        <div class="hero"><div class="eyebrow">INDONESIAN JOB INTELLIGENCE · PORTFOLIO MVP</div>
        <h1>SkillPulse AI</h1>
        <p>Pahami kecocokan CV, bukti requirement, dan prioritas belajar—tanpa black-box ranking.</p></div>
        """,
        unsafe_allow_html=True,
    )
    client = SkillPulseAPIClient(os.getenv("SKILLPULSE_API_URL", "http://127.0.0.1:8000"))
    with st.sidebar:
        st.subheader("System status")
        try:
            health = client.health()
            st.success(f"API online · contract {health['contract_version']}")
        except SkillPulseAPIError as error:
            st.error(str(error))
        st.divider()
        st.markdown("**Privacy by design**")
        st.caption("Teks diproses secara stateless. Demo tidak menyimpan CV dan tidak memakai atribut terlindungi.")
        st.markdown("**Evidence status**")
        st.caption("ML-QG-2/3 masih terbuka. Metrik AI/synthetic adalah diagnostic evidence, bukan human validation.")

    match_tab, extraction_tab, methodology_tab = st.tabs(["CV–Job Match", "Extract Job", "Methodology"])
    with match_tab:
        left, right = st.columns(2)
        cv_text = left.text_area("CV text", value=EXAMPLE_CV, height=230)
        job_text = right.text_area("Job description", value=EXAMPLE_JOB, height=230)
        if st.button("Analyze match", type="primary", use_container_width=True):
            try:
                _render_match(client.match(cv_text, job_text))
            except SkillPulseAPIError as error:
                st.error(str(error))
    with extraction_tab:
        job_text = st.text_area("Job description to extract", value=EXAMPLE_EXTRACTION, height=250)
        if st.button("Extract requirements", use_container_width=True):
            try:
                _render_extraction(client.extract(job_text))
            except SkillPulseAPIError as error:
                st.error(str(error))
    with methodology_tab:
        st.subheader("How the score works")
        st.write(
            "Matcher v0.1 menilai requirement eksplisit per kategori: technical skills 30%, tools 25%, "
            "soft skills 10%, education 10%, experience 15%, seniority 5%, dan work arrangement 5%. "
            "Bobot dinormalisasi hanya pada kategori yang terdeteksi."
        )
        st.subheader("Why the semantic model is not live")
        st.write(
            "Multilingual MiniLM telah diuji sebagai 20% hybrid challenger pada 50 pasangan sintetis, "
            "tetapi error dan latency memburuk. Baseline explainable dipertahankan sampai tersedia "
            "human relevance benchmark."
        )
        st.warning("SkillPulse adalah decision support, bukan alat auto-reject atau penilaian nilai kandidat.")


render()
