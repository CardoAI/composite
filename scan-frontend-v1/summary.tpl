{{- define "cell" -}}
{{- printf "%v" . | trunc 120 | html | replace "\\" "&#92;" | replace "|" "&#124;" | replace "`" "&#96;" | replace "[" "&#91;" | replace "]" "&#93;" | replace "*" "&#42;" | replace "_" "&#95;" | replace "\n" " " | replace "\r" " " -}}
{{- end -}}
{{- define "severity" -}}
{{- $icons := dict "CRITICAL" "🔴" "HIGH" "🟠" "MEDIUM" "🟡" "LOW" "🔵" "UNKNOWN" "⚫" -}}
{{ get $icons . }} {{ . }}
{{- end -}}
{{- define "table-header" -}}
| Vulnerability | Severity | Package | Installed | Fixed versions | Manifest | {{ if eq (env "SCAN_MODE") "report-only" }}Blocks in normal mode{{ else }}Blocks deployment{{ end }} |
| --- | --- | --- | --- | --- | --- | --- |
{{- end -}}
{{- $severities := list "CRITICAL" "HIGH" "MEDIUM" "LOW" "UNKNOWN" -}}
{{- $counts := dict "CRITICAL" 0 "HIGH" 0 "MEDIUM" 0 "LOW" 0 "UNKNOWN" 0 -}}
{{- $findings := list -}}
{{- $blocking := 0 -}}
{{- range . -}}
    {{- $target := .Target -}}
    {{- range .Vulnerabilities -}}
        {{- $_ := set $counts .Severity (add1 (get $counts .Severity)) -}}
        {{- $findings = append $findings (dict "target" $target "vulnerability" .) -}}
        {{- if and (eq .Severity "CRITICAL") .FixedVersion -}}
            {{- $blocking = add1 $blocking -}}
        {{- end -}}
    {{- end -}}
{{- end -}}
### 📊 Scan Summary

| Category | 🔴 Critical | 🟠 High | 🟡 Medium | 🔵 Low | ⚫ Unknown | **Total** | 🛠️ Fixable critical |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 🛡️ **Vulnerabilities** | {{ get $counts "CRITICAL" }} | {{ get $counts "HIGH" }} | {{ get $counts "MEDIUM" }} | {{ get $counts "LOW" }} | {{ get $counts "UNKNOWN" }} | **{{ len $findings }}** | **{{ $blocking }}** |

### 🔍 Vulnerabilities Found

{{ if not $findings -}}
**No dependency vulnerabilities detected.**
{{ else -}}
{{ template "table-header" }}
{{- $shown := 0 -}}
{{- range $severity := $severities -}}
    {{- range $findings -}}
        {{- $v := .vulnerability -}}
        {{- if and (eq $v.Severity $severity) (lt $shown 100) }}
            {{- if eq $shown 10 }}

<details>
<summary>Show {{ sub (min (len $findings) 100) 10 }} more</summary>

{{ template "table-header" }}
            {{- end }}
| {{ template "cell" $v.VulnerabilityID }} | {{ template "severity" $v.Severity }} | {{ template "cell" $v.PkgName }} | {{ template "cell" $v.InstalledVersion }} | {{ if $v.FixedVersion }}{{ template "cell" $v.FixedVersion }}{{ else }}No fix available{{ end }} | {{ template "cell" .target }} | {{ if and (eq $v.Severity "CRITICAL") $v.FixedVersion }}Yes{{ else }}No{{ end }} |
            {{- $shown = add1 $shown -}}
        {{- end -}}
    {{- end -}}
{{- end }}

{{ if gt $shown 10 }}</details>

{{ end -}}
{{ if gt (len $findings) 100 -}}
Showing the first 100 findings, ordered by severity. See the scan logs for all findings and complete field values.
{{ end -}}
{{ end -}}
