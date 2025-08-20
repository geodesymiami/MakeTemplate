import os
import glob
import unittest
import subprocess

class TestCreateInsarTemplate(unittest.TestCase):
    def test_template_creation(self):
        # Define input arguments
        xlsfile_path = os.path.join(os.getcwd(), "docs", "Central_America.xlsx")
        output_dir = os.path.join(os.getcwd(), "output")

        os.makedirs(output_dir, exist_ok=True)

        input_args = ["python", "MakeTemplate/src/maketemplate/create_insar_template.py","--xlsfile", xlsfile_path,"--save","--dir", output_dir]

        # Run the script
        result = subprocess.run(input_args, capture_output=True, text=True)

        # Assert the script ran successfully
        self.assertEqual(result.returncode, 0, f"Script failed with error: {result.stderr}")

        # Use a wildcard to match output files
        output_files = glob.glob(os.path.join(output_dir, "test_template*.template"))

        # Assert that at least one matching file exists
        self.assertTrue(len(output_files) > 0, "No matching output files were created.")

        # Clean up: Remove all matching files
        for file in output_files:
            os.remove(file)

if __name__ == "__main__":
    unittest.main()