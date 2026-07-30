# Allow inbound connections to the IFE ReviewDB dashboard on TCP port 5000
# so other machines on the office network can reach it.
#
# Run this ONCE, as Administrator:
#   Right-click PowerShell -> "Run as administrator", then:
#   powershell -ExecutionPolicy Bypass -File add_firewall_rule.ps1
#
# To remove it later:
#   Remove-NetFirewallRule -DisplayName "IFE ReviewDB (port 5000)"

$name = "IFE ReviewDB (port 5000)"
$existing = Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue
if ($existing) {
    Write-Output "Firewall rule already exists: $name"
} else {
    New-NetFirewallRule -DisplayName $name `
        -Direction Inbound -Action Allow `
        -Protocol TCP -LocalPort 5000 `
        -Profile Private,Domain | Out-Null
    Write-Output "Created firewall rule allowing inbound TCP 5000: $name"
}
