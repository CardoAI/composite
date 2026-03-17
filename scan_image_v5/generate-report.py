import json
import os
import sys  # Import the sys module


def create_markdown_report(data):
    """
    Generates a complete Markdown report string from the JSON data.
    """

    # --- 1. Beautified Summary Table ---
    vuln_summary = data.get("VulnerabilitiesSummary", {})
    vuln_count = vuln_summary.get("count", 0)
    vuln_sev = vuln_summary.get("severities", {})

    det_summary = data.get("DetectionsSummary", {})
    det_count = det_summary.get("count", 0)
    det_sev = det_summary.get("severities", {})

    summary_md = (
        "### 📊 Scan Summary\n\n"
        "| Category | 🔴 Critical | 🟠 High | 🟡 Medium | 🔵 Low | ⚫ Unknown | **Total** |\n"
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |\n"
        f"| 🛡️ **Vulnerabilities** | {vuln_sev.get('critical', 0)} | {vuln_sev.get('high', 0)} | "
        f"{vuln_sev.get('medium', 0)} | {vuln_sev.get('low', 0)} | {vuln_sev.get('unknown', 0)} | "
        f"**{vuln_count}** |\n"
        f"| 🚨 **Detections** | {det_sev.get('critical', 0)} | {det_sev.get('high', 0)} | "
        f"{det_sev.get('medium', 0)} | {det_sev.get('low', 0)} | {det_sev.get('unknown', 0)} | "
        f"**{det_count}** |\n"
    )

    # --- 2. Vulnerabilities Table ---
    vulnerabilities = data.get("Vulnerabilities", [])
    vuln_table_md = "\n### 🔍 Vulnerabilities Found\n\n"
    if vulnerabilities:
        # Define the order of severities
        exprt_rating = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}

        # Sort the vulnerabilities list based on the exprt_rating order
        sorted_vulnerabilities = sorted(
            vulnerabilities,
            key=lambda item: exprt_rating.get(
                item.get("Vulnerability", {}).get("Details", {}).get("exprt_rating", "UNKNOWN").upper(),
                99,  # Default value for any unexpected severities, placing them at the end
            ),
        )

        vuln_table_md += "| VULNERABILITY | EXPRT RATING | SEVERITY | SCORE | EXPLOIT STATUS | PACKAGE | INSTALLED VERSION | PATH | FIXED VERSION | DESCRIPTION |\n"
        vuln_table_md += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"

        for item in sorted_vulnerabilities:
            # (The rest of this function remains the same as before)
            vuln_data = item.get("Vulnerability", {})
            details = vuln_data.get("Details", {})
            product = vuln_data.get("Product", {})
            exploit_details = vuln_data.get("ExploitDetails", {})
            cve_id = vuln_data.get("CVEID", "N/A")
            exprt_rating = details.get("cps_rating", {}).get("CurrentRating", {}).get("Rating", "N/A")
            severity = details.get("severity", "N/A")
            score = details.get("base_score", "N/A")
            if exploit_details.get("exploit_found"):
                maturity = exploit_details.get("max_exploit_maturity", "")
                exploit_status = f"Available ({maturity})" if maturity else "Available"
            else:
                exploit_status = "Unproven"
            package = product.get("Product", "N/A")
            installed_version = product.get("MajorVersion", "N/A")
            path = "N/A"
            fixed_versions = vuln_data.get("FixedVersions", [])
            fixed_version = fixed_versions[0] if fixed_versions else "No fix"
            description = (details.get("description", "N/A")[:50] + "...").replace("\n", " ")
            vuln_table_md += f"| {cve_id} | {exprt_rating} | {severity} | {score} | {exploit_status} | `{package}` | `{installed_version}` | {path} | `{fixed_version}` | {description} |\n"

    # --- 3. Detections Table ---
    detections = data.get("Detections", [])
    det_table_md = "\n### 🚨 Detections Found\n\n"
    if detections:
        det_table_md += "| TYPE | SEVERITY | NAME | TITLE | DESCRIPTION | REMEDIATION | DETAILS |\n"
        det_table_md += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"

        for item in detections:
            detection_data = item.get("Detection", {})
            dtype = detection_data.get("Type", "N/A")
            severity = detection_data.get("Severity", "N/A")
            name = detection_data.get("Name", "N/A")
            title = detection_data.get("Title", "N/A")
            description = (detection_data.get("Description", "N/A")[:25] + "...").replace("\n", " ")
            remediation = (detection_data.get("Remediation", "N/A")[:25] + "...").replace("\n", " ")
            details_obj = detection_data.get("Details") or {}
            if isinstance(details_obj, dict):
                details = details_obj.get("Match", "N/A")
            else:
                details = "N/A"
            det_table_md += (
                f"| {dtype} | {severity} | {name} | {title} | {description} | {remediation} | `{details}` |\n"
            )

    return summary_md + vuln_table_md + det_table_md


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Error: Please provide the path to the JSON report file as an argument.")
        sys.exit(1)

    json_file_path = sys.argv[1]

    try:
        with open(json_file_path, "r") as f:
            report_data = json.load(f)

        markdown_output = create_markdown_report(report_data)

        summary_file = os.getenv("GITHUB_STEP_SUMMARY")
        if summary_file:
            with open(summary_file, "a") as f:
                f.write(markdown_output)
            print("✅ Successfully generated and appended report to GitHub Job Summary.")
        else:
            print("Not in a GitHub Action environment. Printing Markdown to console:\n")
            print(markdown_output)

    except FileNotFoundError:
        print(f"❌ Error: The file '{json_file_path}' was not found.")
    except json.JSONDecodeError:
        print(f"❌ Error: Failed to parse JSON from '{json_file_path}'.")
