import os
import glob
import unittest
import subprocess

class TestCreateInsarTemplate(unittest.TestCase):
    def test_template_creation(self):
        # Define paths
        project_root = os.getcwd()  # Get the current working directory
        script_path = os.path.join(project_root, "src", "maketemplate", "cli", "create_insar_template.py")
        xlsfile_path = os.path.join(project_root, "docs", "Central_America.xlsx")
        output_dir = os.path.join(project_root, "output")

        os.makedirs(output_dir, exist_ok=True)

        # Add src directory to PYTHONPATH
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.join(project_root, "src")
        print(f"PYTHONPATH: {env['PYTHONPATH']}")  # Debug print

        input_args = ["python", "-m", "maketemplate.cli.create_insar_template","--xlsfile", xlsfile_path, "--save", "--dir", output_dir]

        # Run the script with the updated environment
        result = subprocess.run(input_args, capture_output=True, text=True, env=env)

        self.assertTrue(os.path.exists(script_path), f"Script file not found: {script_path}")

        # Assert the script ran successfully
        self.assertEqual(result.returncode, 0, f"Script failed with error: {result.stderr}")

        # Use a wildcard to match output files
        output_files = glob.glob(os.path.join(output_dir, "test_template*.template"))

        print(f"Output files found: {output_files}")

        # Assert that at least one matching file exists
        self.assertTrue(len(output_files) > 0, "No matching output files were created.")

        # Clean up: Remove all matching files
        for file in output_files:
            os.remove(file)

if __name__ == "__main__":
    unittest.main()