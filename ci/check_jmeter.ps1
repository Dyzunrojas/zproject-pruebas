param(
  [Parameter(Mandatory=$true)][string]$Jtl,
  [double]$MaxErrorPct = 1.0
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path $Jtl)) { throw "No existe el archivo de resultados: $Jtl" }
$rows = @(Import-Csv $Jtl)
if ($rows.Count -eq 0) { throw "El archivo de resultados esta vacio" }

Write-Host ""
Write-Host "=== Resumen JMeter por peticion ==="
$rows | Group-Object label | ForEach-Object {
  $t = @($_.Group | ForEach-Object { [int]$_.elapsed } | Sort-Object)
  $n = $t.Count
  $avg = [math]::Round((($t | Measure-Object -Average).Average), 0)
  $p95 = $t[[math]::Max(0, [math]::Ceiling($n * 0.95) - 1)]
  $err = @($_.Group | Where-Object { $_.success -ne 'true' }).Count
  "{0,-40} muestras={1,4} promedio={2,5} ms p95={3,5} ms errores={4}" -f $_.Name, $n, $avg, $p95, $err
}

$total = $rows.Count
$errors = @($rows | Where-Object { $_.success -ne 'true' }).Count
$pct = [math]::Round(100.0 * $errors / $total, 2)
Write-Host ""
Write-Host "Total de peticiones: $total | Errores: $errors ($pct %) | Maximo permitido: $MaxErrorPct %"
if ($pct -gt $MaxErrorPct) { throw "Rendimiento: demasiados errores ($pct %)" }
Write-Host "Prueba de rendimiento aprobada"
