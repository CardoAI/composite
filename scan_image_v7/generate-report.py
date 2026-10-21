import json
import os
import sys  # Import the sys module


# Number of rows shown before the "Show more" toggle
VISIBLE_ROWS = 10


def get_exprt_rating(vuln_data):
    """
    Returns the current ExPRT rating of a vulnerability, or None when CrowdStrike didn't provide one
    (the cps_rating fields can be missing or null).
    """
    details = vuln_data.get("Details") or {}
    return ((details.get("cps_rating") or {}).get("CurrentRating") or {}).get("Rating")


def render_collapsible_table(table_header, rows, label):
    """
    Renders the first VISIBLE_ROWS rows as a table and collapses the rest behind a "Show more" toggle.
    """
    table_md = table_header + "".join(rows[:VISIBLE_ROWS])
    hidden_rows = rows[VISIBLE_ROWS:]
    if hidden_rows:
        table_md += (
            f"\n<details>\n<summary>Show {len(hidden_rows)} more {label}</summary>\n\n"
            + table_header
            + "".join(hidden_rows)
            + "\n</details>\n"
        )
    return table_md


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
        exprt_rating_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}

        # Sort the vulnerabilities list based on the exprt_rating order
        sorted_vulnerabilities = sorted(
            [item for item in vulnerabilities if item],
            key=lambda item: exprt_rating_order.get(
                (get_exprt_rating(item.get("Vulnerability") or {}) or "UNKNOWN").upper(),
                99,  # Default value for any unexpected severities, placing them at the end
            ),
        )

        table_header = (
            "| VULNERABILITY | EXPRT RATING | SEVERITY | SCORE | EXPLOIT STATUS | PACKAGE | INSTALLED VERSION | PATH | FIXED VERSION | DESCRIPTION |\n"
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
        )
        vuln_rows = []

        for item in sorted_vulnerabilities:
            # (The rest of this function remains the same as before)
            vuln_data = item.get("Vulnerability", {})
            details = vuln_data.get("Details", {})
            product = vuln_data.get("Product", {})
            exploit_details = vuln_data.get("ExploitDetails", {})
            cve_id = vuln_data.get("CVEID", "N/A")
            exprt_rating = get_exprt_rating(vuln_data) or "N/A"
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
            vuln_rows.append(
                f"| {cve_id} | {exprt_rating} | {severity} | {score} | {exploit_status} | `{package}` | `{installed_version}` | {path} | `{fixed_version}` | {description} |\n"
            )

        vuln_table_md += render_collapsible_table(table_header, vuln_rows, "vulnerabilities")

    # --- 3. Detections Table ---
    detections = data.get("Detections", [])
    det_table_md = "\n### 🚨 Detections Found\n\n"
    if detections:
        table_header = (
            "| TYPE | SEVERITY | NAME | TITLE | DESCRIPTION | REMEDIATION | DETAILS |\n"
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
        )
        det_rows = []

        for item in detections:
            if not item:
                continue
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
            det_rows.append(
                f"| {dtype} | {severity} | {name} | {title} | {description} | {remediation} | `{details}` |\n"
            )

        det_table_md += render_collapsible_table(table_header, det_rows, "detections")

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
