{{- $lockfile := env "EXPECTED_LOCKFILE" -}}
{{- $packages := 0 -}}
{{- range . -}}
    {{- if and (eq .Target $lockfile) (eq .Class "lang-pkgs") (has (printf "%s" .Type) (list "yarn" "npm" "pnpm" "bun")) -}}
        {{- range .Packages -}}
            {{- if and .Name .Version -}}
                {{- $packages = add1 $packages -}}
            {{- end -}}
        {{- end -}}
    {{- end -}}
{{- end -}}
{{- if eq $packages 0 -}}
    {{- fail (printf "Dependency scan incomplete: no resolved packages were analyzed in %s. Check the lockfile format and Trivy skip settings." $lockfile) -}}
{{- end -}}
