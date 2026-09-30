$loginBody = @{username="admin"; password="123456"} | ConvertTo-Json
$loginResult = Invoke-WebRequest -Uri "http://localhost:8088/api/auth/login" -Method POST -Body $loginBody -ContentType "application/json" -UseBasicParsing
$obj = $loginResult.Content | ConvertFrom-Json
$token = $obj.data.token
$authHeaders = @{Authorization = "Bearer $token"}
Write-Host "Login OK"

# Medical
$body = @{name="Test"; age=30; gender="M"; symptoms="fever,cough,headache"; durationDays=3; history=""; medications=""} | ConvertTo-Json
$r = Invoke-WebRequest -Uri "http://localhost:8088/api/medical/ai-doctor/consult" -Method POST -Body $body -ContentType "application/json" -Headers $authHeaders -UseBasicParsing
$j = $r.Content | ConvertFrom-Json
if ($j.code -eq 200) { Write-Host "Medical: OK" } else { Write-Host "Medical: FAIL" }

# Finance suspicious
$r = Invoke-WebRequest -Uri "http://localhost:8088/api/finance/analysis/suspicious" -Method GET -Headers $authHeaders -UseBasicParsing
$j = $r.Content | ConvertFrom-Json
if ($j.code -eq 200) { Write-Host ("Finance Suspicious: OK - " + $j.data.Count + " results") } else { Write-Host "Finance Suspicious: FAIL" }

# Environment prediction
$r = Invoke-WebRequest -Uri "http://localhost:8088/api/environment/analysis/prediction?days=3" -Method GET -Headers $authHeaders -UseBasicParsing
$j = $r.Content | ConvertFrom-Json
if ($j.code -eq 200) { Write-Host ("Env Prediction: OK - " + $j.data.Count + " days") } else { Write-Host "Env Prediction: FAIL" }

# Environment health index
$r = Invoke-WebRequest -Uri "http://localhost:8088/api/environment/analysis/health-index" -Method GET -Headers $authHeaders -UseBasicParsing
$j = $r.Content | ConvertFrom-Json
if ($j.code -eq 200) { Write-Host ("Env Health Index: OK - isMlGenerated=" + $j.data.isMlGenerated) } else { Write-Host "Env Health Index: FAIL" }

# Energy device analysis
$r = Invoke-WebRequest -Uri "http://localhost:8088/api/energy/analysis/device" -Method GET -Headers $authHeaders -UseBasicParsing
$j = $r.Content | ConvertFrom-Json
if ($j.code -eq 200) { Write-Host ("Energy Device: OK - isCarbonMlEstimated=" + $j.data.isCarbonMlEstimated) } else { Write-Host "Energy Device: FAIL" }

# Energy prediction
$r = Invoke-WebRequest -Uri "http://localhost:8088/api/energy/analysis/prediction?days=3" -Method GET -Headers $authHeaders -UseBasicParsing
$j = $r.Content | ConvertFrom-Json
if ($j.code -eq 200) { Write-Host ("Energy Prediction: OK - " + $j.data.Count + " days") } else { Write-Host "Energy Prediction: FAIL" }

# Traffic prediction
$r = Invoke-WebRequest -Uri "http://localhost:8088/api/traffic/analysis/prediction" -Method GET -Headers $authHeaders -UseBasicParsing
$j = $r.Content | ConvertFrom-Json
if ($j.code -eq 200) { Write-Host ("Traffic: OK - " + $j.data.Count + " hours") } else { Write-Host "Traffic: FAIL" }

# Finance trend
$r = Invoke-WebRequest -Uri "http://localhost:8088/api/finance/analysis/trend-prediction?days=3" -Method GET -Headers $authHeaders -UseBasicParsing
$j = $r.Content | ConvertFrom-Json
if ($j.code -eq 200) { Write-Host ("Finance Trend: OK - " + $j.data[0].isMlGenerated) } else { Write-Host "Finance Trend: FAIL" }

Write-Host "All tests done."
