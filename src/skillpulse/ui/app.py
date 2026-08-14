"""Streamlit portfolio experience for SkillPulse AI."""

from __future__ import annotations

import os
from typing import Any

import streamlit as st

from skillpulse.feedback import (
    ExtractionFeedbackContext,
    build_extraction_feedback,
    extraction_feedback_context,
    feedback_json,
)
from skillpulse.ui.api_client import SkillPulseAPIClient, SkillPulseAPIError
from skillpulse.ui.examples import EXAMPLE_CV, EXAMPLE_EXTRACTION, EXAMPLE_JOB
from skillpulse.ui.market import (
    CATEGORY_LABELS,
    load_market_snapshot,
    market_slice,
    market_slice_options,
    top_rows,
    top_skill_rows,
)


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


def _clear_extraction_feedback() -> None:
    for key in (
        "extraction_feedback_context",
        "extraction_feedback_incorrect",
        "extraction_feedback_confirmed",
    ):
        st.session_state.pop(key, None)


def _render_extraction_feedback(context: ExtractionFeedbackContext) -> None:
    st.markdown("### Koreksi hasil extraction")
    st.caption(
        "Review ini hanya mengekspor canonical label dan verdict. Job text, matched text, source span, "
        "dan identitas tidak disertakan atau dikirim ke server."
    )
    if not context.candidates:
        st.info("Belum ada canonical entity yang dapat direview.")
        return

    labels = {candidate.id: candidate.label for candidate in context.candidates}
    incorrect = st.multiselect(
        "Tandai entity yang tidak tepat",
        options=list(labels),
        format_func=labels.__getitem__,
        key="extraction_feedback_incorrect",
        help="Entity yang tidak dipilih akan ditandai correct setelah review dikonfirmasi.",
    )
    confirmed = st.checkbox(
        "Saya telah memeriksa seluruh entity di atas",
        key="extraction_feedback_confirmed",
    )
    data = ""
    if confirmed:
        record = build_extraction_feedback(
            context,
            incorrect_ids=set(incorrect),
            review_confirmed=True,
        )
        data = feedback_json(record)
    st.download_button(
        "Unduh feedback tanpa teks mentah",
        data=data,
        file_name="skillpulse_extraction_feedback.json",
        mime="application/json",
        disabled=not confirmed,
        use_container_width=True,
    )
    st.caption("Download dibuat di memori sesi browser dan tidak disimpan otomatis oleh SkillPulse.")


@st.cache_data(show_spinner=False)
def _market_snapshot() -> dict[str, Any]:
    return load_market_snapshot()


def _render_market_snapshot() -> None:
    try:
        snapshot = _market_snapshot()
    except (FileNotFoundError, ValueError) as error:
        st.error(f"Market snapshot belum tersedia: {error}")
        return

    source = snapshot["source"]
    window = source["observation_window"]
    summary = snapshot["summary"]
    st.subheader("30-day market snapshot")
    st.write(
        "Ringkasan deskriptif lowongan data dan analytics pada satu dataset Indonesia. "
        "Gunakan untuk eksplorasi requirement, bukan sebagai klaim tren atau keseluruhan pasar."
    )
    st.caption(
        f"{window['start']} hingga {window['end']} · Kaggle version {source['version']} · "
        f"{source['license']} · satu source portal"
    )

    first, second, third, fourth = st.columns(4)
    first.metric("Listings in snapshot", f"{summary['total_listings']:,}")
    second.metric("Unique descriptions", f"{summary['unique_descriptions']:,}")
    third.metric("Reported provinces", summary["reported_provinces"])
    fourth.metric(
        "Salary disclosed",
        f"{summary['salary_disclosed_listings']} ({100 * summary['salary_disclosure_rate']:.1f}%)",
    )

    province_leader = top_rows(snapshot, "province_counts", 1)[0]
    st.info(
        f"Coverage is concentrated: {province_leader['label']} contributes "
        f"{province_leader['count']}/{summary['total_listings']} listings "
        f"({100 * province_leader['share']:.1f}%). Read location comparisons as source composition."
    )

    st.markdown("### Explicit requirement demand")
    segment_options = market_slice_options(snapshot)
    segment_label = st.selectbox(
        "Market segment",
        list(segment_options),
        key="market_segment",
        help="Choose one privacy-safe aggregate by location or normalized job title.",
    )
    selected_slice = market_slice(snapshot, segment_options[segment_label])
    label_to_category = {label: key for key, label in CATEGORY_LABELS.items()}
    category_label = st.selectbox(
        "Requirement category",
        list(label_to_category),
        key="market_skill_category",
        help="This local filter changes only the requirement chart.",
    )
    top_n = st.select_slider(
        "Requirements shown",
        options=[10, 15, 20],
        value=15,
        key="market_skill_limit",
    )
    skill_rows = top_skill_rows(
        snapshot,
        label_to_category[category_label],
        top_n,
        slice_id=selected_slice["id"],
    )
    chart_rows = [{"Requirement": row["label"], "Descriptions": row["count"]} for row in skill_rows]
    st.bar_chart(
        chart_rows,
        x="Descriptions",
        y="Requirement",
        horizontal=True,
        color="#0e7490",
        height=430,
    )
    st.caption(
        f"Active filter: {selected_slice['label']} · denominator: "
        f"{selected_slice['unique_descriptions']} exact-unique descriptions from "
        f"{selected_slice['listing_count']} listings. Each canonical requirement counts at most once "
        "per description; extraction is rule-based."
    )

    location_column, seniority_column = st.columns(2)
    with location_column:
        st.markdown("### Location mix")
        province_rows = [
            {"Province": row["label"], "Listings": row["count"]}
            for row in top_rows(snapshot, "province_counts", 8)
        ]
        st.bar_chart(
            province_rows,
            x="Listings",
            y="Province",
            horizontal=True,
            color="#ea580c",
            height=360,
        )
    with seniority_column:
        st.markdown("### Source-provided seniority")
        seniority_rows = [
            {"Seniority": row["label"], "Listings": row["count"]}
            for row in top_rows(snapshot, "seniority_counts", 10)
        ]
        st.bar_chart(
            seniority_rows,
            x="Listings",
            y="Seniority",
            horizontal=True,
            color="#7c3aed",
            height=360,
        )
        st.caption("Missing source labels remain visible as Unknown; they are not model-inferred.")

    st.markdown("### Most repeated normalized titles")
    title_rows = [
        {
            "Job title": row["label"],
            "Listings": row["count"],
            "Share of snapshot": f"{100 * row['share']:.1f}%",
        }
        for row in top_rows(snapshot, "title_counts", 10)
    ]
    st.table(title_rows)
    st.caption(
        f"Case and whitespace variants are merged. Groups below {snapshot['suppression']['minimum_published_count']} "
        "listings are omitted from the public aggregate."
    )
    st.warning(
        "Only 77/555 listings disclose salary, and this dataset contains one 30-day window. "
        "Salary prediction and time-series claims remain intentionally disabled."
    )
    st.markdown(f"Source: [{source['title']}]({source['url']}) by {source['creator']}.")


def render(client: SkillPulseAPIClient | None = None) -> None:
    st.set_page_config(page_title="SkillPulse AI", page_icon="📈", layout="wide")
    st.markdown(
        """
        <style>
        .stApp {background: linear-gradient(145deg, #f6fbff 0%, #f8fafc 48%, #fff7ed 100%);}
        [data-testid="stMetric"] {background:#ffffff;border:1px solid #dbe7f0;padding:16px;border-radius:16px;}
        .hero {padding:1.6rem 1.8rem;border-radius:24px;background:linear-gradient(120deg,#0f172a,#164e63);
               color:white;margin-bottom:1.2rem;box-shadow:0 18px 45px rgba(15,23,42,.16)}
        .hero p {color:#d8f3f6;margin-bottom:0}.eyebrow {font-size:.78rem;letter-spacing:.14em;color:#67e8f9}
        @media (max-width: 640px) {
          .hero {padding:1.2rem 1rem;border-radius:18px}.hero h1 {font-size:2rem}
          [data-testid="stMetric"] {padding:12px}
        }
        </style>
        <div class="hero"><div class="eyebrow">INDONESIAN JOB INTELLIGENCE · PORTFOLIO MVP</div>
        <h1>SkillPulse AI</h1>
        <p>Pahami kecocokan CV, bukti requirement, dan prioritas belajar—tanpa black-box ranking.</p></div>
        """,
        unsafe_allow_html=True,
    )
    client = client or SkillPulseAPIClient(os.getenv("SKILLPULSE_API_URL", "http://127.0.0.1:8000"))
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

    match_tab, extraction_tab, market_tab, methodology_tab = st.tabs(
        ["CV–Job Match", "Extract Job", "Market Snapshot", "Methodology"]
    )
    with match_tab:
        if st.button("Gunakan data contoh", key="load_match_example", use_container_width=True):
            st.session_state["match_cv_text"] = EXAMPLE_CV
            st.session_state["match_job_text"] = EXAMPLE_JOB
        left, right = st.columns(2)
        cv_text = left.text_area(
            "CV text",
            value="",
            key="match_cv_text",
            height=230,
            placeholder="Tempel ringkasan CV tanpa nama, email, nomor telepon, atau alamat.",
        )
        job_text = right.text_area(
            "Job description",
            value="",
            key="match_job_text",
            height=230,
            placeholder="Tempel requirement pekerjaan yang ingin dibandingkan.",
        )
        if st.button("Analyze match", key="analyze_match", type="primary", use_container_width=True):
            if not cv_text.strip() or not job_text.strip():
                st.error("Isi CV dan job description sebelum menjalankan analisis.")
            else:
                try:
                    with st.spinner("Menganalisis requirement dan skill gap…"):
                        _render_match(client.match(cv_text, job_text))
                except SkillPulseAPIError as error:
                    st.error(str(error))
        else:
            st.info("Hasil explainable match akan muncul di sini setelah analisis.")
    with extraction_tab:
        if st.button("Gunakan contoh extraction", key="load_extraction_example", use_container_width=True):
            _clear_extraction_feedback()
            st.session_state["extraction_job_text"] = EXAMPLE_EXTRACTION
        extraction_text = st.text_area(
            "Job description to extract",
            value="",
            key="extraction_job_text",
            height=250,
            placeholder="Tempel job description untuk mengekstrak requirement eksplisit.",
            on_change=_clear_extraction_feedback,
        )
        if st.button("Extract requirements", key="extract_requirements", use_container_width=True):
            if not extraction_text.strip():
                st.error("Isi job description sebelum menjalankan extraction.")
            else:
                try:
                    with st.spinner("Mengekstrak requirement eksplisit…"):
                        payload = client.extract(extraction_text)
                        _render_extraction(payload)
                        _clear_extraction_feedback()
                        st.session_state["extraction_feedback_context"] = extraction_feedback_context(payload)
                except SkillPulseAPIError as error:
                    st.error(str(error))
        else:
            st.info("Entity hasil extraction akan muncul di sini setelah diproses.")
        feedback_context = st.session_state.get("extraction_feedback_context")
        if isinstance(feedback_context, ExtractionFeedbackContext):
            _render_extraction_feedback(feedback_context)
    with market_tab:
        _render_market_snapshot()
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


if __name__ == "__main__":
    render()
