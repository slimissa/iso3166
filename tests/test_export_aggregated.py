import subprocess
import sys
import pytest
import pandas as pd
from pathlib import Path

# The tools expect to be run from the repo root, and look for relative paths.
# We will use monkeypatch to change the current working directory to tmp_path
# so the tests are fully isolated.

@pytest.fixture
def mock_repo(tmp_path, monkeypatch):
    """
    Creates an isolated temporary directory with dummy CURATED data.
    Changes the working directory to this temp dir.
    """
    monkeypatch.chdir(tmp_path)
    
    # Create a minimal, valid CURATED parquet file
    # We include a null subregion and a non-null one to test grouping
    dummy_data = pd.DataFrame({
        "alpha_2": ["US", "CA", "MX", "AQ"],
        "region": ["Americas", "Americas", "Americas", "Antarctica"],
        "subregion": ["Northern America", "Northern America", "Central America", None],
        "independent": [True, True, True, False]
    })
    
    # The script expects this specific filename
    dummy_data.to_parquet("iso3166.parquet", index=False)
    
    return tmp_path

def run_script(*args):
    """Helper to run the export script as a subprocess."""
    return subprocess.run(
        [sys.executable, "tools/export_aggregated.py", *args],
        capture_output=True,
        text=True
    )

def test_generate_happy_path(mock_repo):
    """Test the standard generation of the AGGREGATED file."""
    # Ensure tools dir exists in the temp path for the subprocess to find the script
    # (Since we changed cwd, we need to link or copy the tool)
    # Alternatively, we can just run the script by absolute path.
    script_path = Path(__file__).parent.parent / "tools" / "export_aggregated.py"
    
    res = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True, text=True, cwd=mock_repo
    )
    
    assert res.returncode == 0
    assert "wrote countries_by_region.parquet" in res.stdout
    
    output_file = mock_repo / "countries_by_region.parquet"
    assert output_file.exists()
    
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
    script_path = Path(__file__).parent.parent / "tools" / "export_aggregated.py"
    
    # First generate the file
    subprocess.run([sys.executable, str(script_path)], cwd=mock_repo)
    
    # Then check it
    res = subprocess.run(
        [sys.executable, str(script_path), "--check"],
        capture_output=True, text=True, cwd=mock_repo
    )
    
    assert res.returncode == 0
    assert "OK" in res.stdout


def test_check_missing_file(mock_repo):
    """Test that --check fails if the aggregated file doesn't exist."""
    script_path = Path(__file__).parent.parent / "tools" / "export_aggregated.py"
    
    res = subprocess.run(
        [sys.executable, str(script_path), "--check"],
        capture_output=True, text=True, cwd=mock_repo
    )
    
    assert res.returncode == 1
    assert "STALE (missing)" in res.stderr


def test_check_content_drift(mock_repo):
    """Test that --check fails if the aggregated file is stale."""
    script_path = Path(__file__).parent.parent / "tools" / "export_aggregated.py"
    
    # Generate valid file
    subprocess.run([sys.executable, str(script_path)], cwd=mock_repo)
    
    # Modify the output to simulate drift
    output_file = mock_repo / "countries_by_region.parquet"
    df = pd.read_parquet(output_file)
    df.loc[0, "country_count"] += 1 # Fake a change
    df.to_parquet(output_file, index=False)
    
    # Check should fail
    res = subprocess.run(
        [sys.executable, str(script_path), "--check"],
        capture_output=True, text=True, cwd=mock_repo
    )
    
    assert res.returncode == 1
    assert "STALE (content mismatch)" in res.stderr
    # Ensure the assertion diff is printed
    assert "DataFrame.iloc" in res.stderr or "are different" in res.stderr


def test_missing_curated_input(mock_repo):
    """Test that the script fails gracefully if iso3166.parquet is missing."""
    script_path = Path(__file__).parent.parent / "tools" / "export_aggregated.py"
    
    # Delete the input
    (mock_repo / "iso3166.parquet").unlink()
    
    res = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True, text=True, cwd=mock_repo
    )
    
    assert res.returncode == 2
    assert "not found. Run tools/export_parquet.py first" in res.stderr


def test_invalid_curated_schema(mock_repo):
    """Test that the script fails if the CURATED layer is missing required columns."""
    script_path = Path(__file__).parent.parent / "tools" / "export_aggregated.py"
    
    # Overwrite the input with a bad schema (missing 'independent')
    bad_data = pd.DataFrame({
        "alpha_2": ["US"],
        "region": ["Americas"],
        "subregion": ["Northern America"]
    })
    bad_data.to_parquet("iso3166.parquet", index=False)
    
    res = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True, text=True, cwd=mock_repo
    )
    
    assert res.returncode == 2
    assert "missing required columns" in res.stderr
    assert "independent" in res.stderr