import hashlib
import subprocess
import sys
import pytest
import pandas as pd
from pathlib import Path

# The tool resolves its default input and output against the repository
# root, so it works from any directory. These tests pass --input and
# --output explicitly, pointing into a temporary directory, so they never
# read or write the committed files. They run with cwd set to that
# directory to show that nothing depends on the current directory.

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "tools" / "export_aggregated.py"


@pytest.fixture
def mock_repo(tmp_path):
    """An isolated temporary directory holding a dummy CURATED parquet file."""
    # A minimal, valid CURATED file: a null subregion and non-null ones, to
    # test grouping.
    dummy_data = pd.DataFrame({
        "alpha_2": ["US", "CA", "MX", "AQ"],
        "region": ["Americas", "Americas", "Americas", "Antarctica"],
        "subregion": ["Northern America", "Northern America", "Central America", None],
        "independent": [True, True, True, False]
    })
    dummy_data.to_parquet(tmp_path / "iso3166.parquet", index=False)
    return tmp_path


def run_script(mock_repo, *args, input_path=None, output_path=None):
    """Run the tool against files in mock_repo, from mock_repo as the cwd."""
    cmd = [
        sys.executable, str(SCRIPT_PATH), *args,
        "--input", str(input_path or mock_repo / "iso3166.parquet"),
        "--output", str(output_path or mock_repo / "countries_by_region.parquet"),
    ]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=mock_repo)


def test_generate_happy_path(mock_repo):
    """Test the standard generation of the AGGREGATED file."""
    committed = REPO_ROOT / "countries_by_region.parquet"
    before = hashlib.sha256(committed.read_bytes()).hexdigest()

    res = run_script(mock_repo)

    assert res.returncode == 0
    output_file = mock_repo / "countries_by_region.parquet"
    assert f"wrote {output_file}" in res.stdout
    assert output_file.exists()
    # The committed artifact is untouched.
    assert hashlib.sha256(committed.read_bytes()).hexdigest() == before
    
    # Verify the actual output data
    df = pd.read_parquet(output_file)
    
    assert list(df.columns) == ["region", "subregion", "country_count", "independent_count"]
    
    # Check the Americas group (US, CA, MX)
    americas = df[df["region"] == "Americas"]
    # It should be grouped by subregion, so there should be 2 rows here
    assert len(americas) == 2
    
    north_america = americas[americas["subregion"] == "Northern America"].iloc[0]
    assert north_america["country_count"] == 2
    assert north_america["independent_count"] == 2
    
    central_america = americas[americas["subregion"] == "Central America"].iloc[0]
    assert central_america["country_count"] == 1
    assert central_america["independent_count"] == 1
    
    # Check the Null subregion group (Antarctica)
    antarctica = df[df["region"] == "Antarctica"].iloc[0]
    assert pd.isna(antarctica["subregion"]) # Null is preserved
    assert antarctica["country_count"] == 1
    assert antarctica["independent_count"] == 0 # False sum is 0


def test_check_happy_path(mock_repo):
    """Test that --check passes when the file is up to date."""
    # First generate the file
    run_script(mock_repo)

    # Then check it
    res = run_script(mock_repo, "--check")
    
    assert res.returncode == 0
    assert "OK" in res.stdout


def test_check_missing_file(mock_repo):
    """Test that --check fails if the aggregated file doesn't exist."""
    res = run_script(mock_repo, "--check")

    assert res.returncode == 1
    assert "STALE (missing)" in res.stderr


def test_check_content_drift(mock_repo):
    """Test that --check fails if the aggregated file is stale."""
    # Generate valid file
    run_script(mock_repo)
    
    # Modify the output to simulate drift
    output_file = mock_repo / "countries_by_region.parquet"
    df = pd.read_parquet(output_file)
    df.loc[0, "country_count"] += 1 # Fake a change
    df.to_parquet(output_file, index=False)
    
    # Check should fail
    res = run_script(mock_repo, "--check")
    
    assert res.returncode == 1
    assert "STALE (content mismatch)" in res.stderr
    # Ensure the assertion diff is printed
    assert "DataFrame.iloc" in res.stderr or "are different" in res.stderr


def test_missing_curated_input(mock_repo):
    """Test that the script fails gracefully if iso3166.parquet is missing."""
    # Delete the input
    (mock_repo / "iso3166.parquet").unlink()

    res = run_script(mock_repo)
    
    assert res.returncode == 2
    assert "not found. Run tools/export_parquet.py first" in res.stderr


def test_invalid_curated_schema(mock_repo):
    """Test that the script fails if the CURATED layer is missing required columns."""
    # Overwrite the input with a bad schema (missing 'independent')
    bad_data = pd.DataFrame({
        "alpha_2": ["US"],
        "region": ["Americas"],
        "subregion": ["Northern America"]
    })
    bad_data.to_parquet(mock_repo / "iso3166.parquet", index=False)

    res = run_script(mock_repo)
    
    assert res.returncode == 2
    assert "missing required columns" in res.stderr
    assert "independent" in res.stderr


def test_default_paths_work_from_any_directory(tmp_path):
    """With no --input/--output the tool uses the repository's own files."""
    res = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--check"],
        capture_output=True, text=True, cwd=tmp_path
    )

    assert res.returncode == 0, res.stderr
    assert "countries_by_region.parquet: OK" in res.stdout
