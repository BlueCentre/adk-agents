from pathlib import Path
import sys
import xml.etree.ElementTree as ET

# Get the coverage XML file path from arguments
if len(sys.argv) < 2:
    print("Usage: python generate_coverage_markdown.py <coverage_xml_path> <output_markdown_path>")
    sys.exit(1)

coverage_xml_path = sys.argv[1]
output_markdown_path = sys.argv[2]

try:
    # Parse coverage XML
    tree = ET.parse(coverage_xml_path)
    root = tree.getroot()

    # Calculate overall coverage
    overall_coverage = float(root.attrib["line-rate"]) * 100

    # Open report file
    with Path.open(output_markdown_path, "w") as f:
        f.write("## Test Coverage Report\n")
        f.write(f"### Overall Coverage: {overall_coverage:.2f}%\n\n")
        f.write("| Module | Coverage |\n")
        f.write("| ------ | -------- |\n")

        # Add each package
        for pkg in root.findall(".//package"):
            pkg_name = pkg.attrib["name"]
            pkg_coverage = float(pkg.attrib["line-rate"]) * 100
            f.write(f"| {pkg_name} | {pkg_coverage:.2f}% |\n")
except FileNotFoundError:
    print(f"Error: Coverage XML file not found at {coverage_xml_path}")
    sys.exit(1)
except ET.ParseError:
    print(f"Error: Failed to parse XML from {coverage_xml_path}")
    sys.exit(1)
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    sys.exit(1)
