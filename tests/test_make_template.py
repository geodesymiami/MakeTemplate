import os
import glob
import subprocess
import pytest


@pytest.fixture
def project_root():
    # Adjust if your tests are not run from repo root
    return os.getcwd()


@pytest.fixture
def env_with_src(project_root):
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.join(project_root, "src")
    return env


def test_create_insar_template(project_root, env_with_src, tmp_path):
    # Paths
    script_path = os.path.join(
        project_root,
        "src",
        "maketemplate",
        "cli",
        "create_insar_template.py",
    )

    xlsfile_path = os.path.join(
        project_root,
        "docs",
        "Central_America.xlsx",
    )

    output_dir = tmp_path  # pytest-managed temporary directory

    # Sanity check: script exists
    assert os.path.exists(script_path), f"Script file not found: {script_path}"
    assert os.path.exists(xlsfile_path), f"Excel file not found: {xlsfile_path}"

    # Command
    cmd = [
        "python",
        "-m",
        "maketemplate.cli.create_insar_template",
        "--xlsfile",
        xlsfile_path,
        "--save",
        "--dir",
        str(output_dir),
    ]

    # Run command
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env_with_src,
    )

    # Assert successful execution
    assert result.returncode == 0, (
        "Script failed\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )

    # Check output files
    output_files = glob.glob(str(output_dir / "*.template"))

    print(f"Output files found: {output_files}")

    assert len(output_files) > 0, "No matching output files were created."