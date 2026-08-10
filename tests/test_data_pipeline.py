import pandas as pd
import pytest

from skillpulse.data.pipeline import prepare_jobs, validate_schema


def sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "posisi": " Data Analyst ",
                "perusahaan": "Example Corp",
                "kota": "Jakarta",
                "provinsi": "DKI Jakarta",
                "gaji": "9500000.0",
                "tools": " SQL,  Power BI ",
                "pendidikan": "S1",
                "pengalaman": "2",
                "deskripsi_lengkap": "Analyze   business data",
                "level": "Junior",
            },
            {
                "posisi": "Data Analyst",
                "perusahaan": "Example Corp",
                "kota": "Jakarta",
                "provinsi": "DKI Jakarta",
                "gaji": "9500000.0",
                "tools": "SQL, Power BI",
                "pendidikan": "S1",
                "pengalaman": 2,
                "deskripsi_lengkap": "Analyze business data",
                "level": "Junior",
            },
        ]
    )


def test_prepare_jobs_normalizes_and_deduplicates() -> None:
    clean, report = prepare_jobs(sample_frame())

    assert len(clean) == 1
    assert clean.loc[0, "job_id"] == "ID-JOB-00001"
    assert clean.loc[0, "posisi"] == "Data Analyst"
    assert clean.loc[0, "deskripsi_lengkap"] == "Analyze business data"
    assert clean.loc[0, "salary_monthly_idr"] == 9_500_000
    assert bool(clean.loc[0, "salary_disclosed"])
    assert report["removed_duplicate_rows"] == 1


def test_prepare_jobs_preserves_missing_salary() -> None:
    frame = sample_frame().iloc[:1].copy()
    frame.loc[0, "gaji"] = None

    clean, report = prepare_jobs(frame)

    assert pd.isna(clean.loc[0, "salary_monthly_idr"])
    assert not bool(clean.loc[0, "salary_disclosed"])
    assert report["salary_disclosure_rate"] == 0.0


def test_validate_schema_reports_missing_columns() -> None:
    with pytest.raises(ValueError, match="Missing required columns"):
        validate_schema(pd.DataFrame({"posisi": ["Data Analyst"]}))

