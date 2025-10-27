# export_env.ps1
# Carga variables de entorno desde un archivo tipo "SECRETOS" con formato KEY=VALUE o "export KEY=VALUE".
# Uso:
#   .\export_env.ps1                # lee SECRETOS en el directorio actual
#   .\export_env.ps1 -SecretFile .\SECRETOS
#   . .\export_env.ps1              # (dot-source) para asegurarte de que persisten en la sesion actual
param(
  [string]$SecretFile = "SECRETOS"
)

if (-not (Test-Path -LiteralPath $SecretFile)) {
  Write-Error "No se encuentra el archivo: $SecretFile"
  exit 1
}

# Lee y exporta
$setVars = @()
Get-Content -LiteralPath $SecretFile | ForEach-Object {
  $line = $_.Trim()
  if ($line -eq "" -or $line.StartsWith("#")) { return }         # comentarios/vacias
  if ($line -match "^\s*export\s+") { $line = $line -replace "^\s*export\s+","" }

  $m = [regex]::Match($line, "^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")
  if (-not $m.Success) { return }

  $key = $m.Groups[1].Value
  $val = $m.Groups[2].Value.Trim()

  # Quita comillas de ambos lados si existen (simples o dobles)
  if (($val.StartsWith('"') -and $val.EndsWith('"')) -or ($val.StartsWith("'") -and $val.EndsWith("'"))) {
    $val = $val.Substring(1, $val.Length - 2)
  }

  # Expande secuencias simples tipo \n \t (opcional; comenta si no lo quieres)
  $val = $val.Replace("`n", "`n").Replace("\n","`n").Replace("\t","`t")

  # Exporta a ENV de esta sesion
  Set-Item -Path Env:$key -Value $val
  $setVars += $key
}

if ($setVars.Count -gt 0) {
  Write-Host ("Variables cargadas: " + ($setVars -join ", "))
  Write-Host "Para verificar, prueba: `"$env:$($setVars[0])`""
} else {
  Write-Host "No se encontraron pares KEY=VALUE en $SecretFile"
}
