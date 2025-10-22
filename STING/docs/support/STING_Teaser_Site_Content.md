<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{{ .Title }} | {{ .Site.Title }}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  {{ if .Site.Params.hero_image }}
    <link rel="preload" href="{{ .Site.Params.hero_image }}" as="image">
  {{ end }}
  <!-- Add any CSS links here -->
  <link rel="stylesheet" href="/css/style.css">
</head>
<body>
  {{ partial "header.html" . }}
  <main>
    {{ block "main" . }}{{ end }}
  </main>
  {{ partial "footer.html" . }}
</body>
</html>
