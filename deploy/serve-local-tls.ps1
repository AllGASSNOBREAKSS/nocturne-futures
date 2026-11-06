[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Python,
    [Parameter(Mandatory = $true)][string]$CertificateFile,
    [Parameter(Mandatory = $true)][string]$PrivateKeyFile,
    [ValidateRange(1024,65535)][int]$Port = 8443
)
$ErrorActionPreference = 'Stop'
if (-not $env:NOCTURNE_API_READER_TOKEN_FILE -and -not $env:NOCTURNE_API_ADMIN_TOKEN_FILE) {
    throw 'Configure protected credential files before starting the API. Never pass token values as arguments.'
}
$CertificateFile = (Resolve-Path $CertificateFile).Path
$PrivateKeyFile = (Resolve-Path $PrivateKeyFile).Path
& $Python -m nocturne serve --host 127.0.0.1 --port $Port --tls-cert-file $CertificateFile --tls-key-file $PrivateKeyFile
exit $LASTEXITCODE
