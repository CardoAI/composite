import json
import sys


def find_fixable_criticals(data):
    """
    Returns the vulnerabilities with a critical ExPRT rating that have at least one fixed version available.
    """
    fixable = []
    for item in data.get("Vulnerabilities") or []:
        vuln_data = (item or {}).get("Vulnerability") or {}
        details = vuln_data.get("Details") or {}
        exprt_rating = ((details.get("cps_rating") or {}).get("CurrentRating") or {}).get("Rating") or ""
        fixed_versions = vuln_data.get("FixedVersions") or []
        if exprt_rating.upper() == "CRITICAL" and fixed_versions:
            fixable.append(vuln_data)
    return fixable


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("::error::Please provide the path to the JSON report file as an argument.")
        sys.exit(1)

    json_file_path = sys.argv[1]

    try:
        with open(json_file_path, "r") as f:
            report_data = json.load(f)
    except FileNotFoundError:
        print(f"::error::The file '{json_file_path}' was not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"::error::Failed to parse JSON from '{json_file_path}'.")
        sys.exit(1)

    fixable_criticals = find_fixable_criticals(report_data)
    if not fixable_criticals:
        print("✅ No vulnerabilities with a critical ExPRT rating and an available fix were found.")
        sys.exit(0)

    for vuln_data in fixable_criticals:
        product = vuln_data.get("Product") or {}
        print(
            f"::error::{vuln_data.get('CVEID', 'N/A')} in {product.get('Product', 'N/A')} "
            f"{product.get('MajorVersion', 'N/A')} has a critical ExPRT rating and is fixed in {', '.join(vuln_data['FixedVersions'])}"
        )
    print(f"❌ Found {len(fixable_criticals)} vulnerabilities with a critical ExPRT rating and an available fix.")
    sys.exit(1)
