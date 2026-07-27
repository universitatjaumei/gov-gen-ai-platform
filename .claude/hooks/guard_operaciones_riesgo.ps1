<#
.SYNOPSIS
    Guarda de riesgo del desarrollo agentico. Decide que comandos puede ejecutar el
    agente sin preguntar y cuales exigen autorizacion humana.

.DESCRIPTION
    Recibe por stdin el JSON del hook de Claude Code y clasifica el comando de la
    herramienta Bash / PowerShell en tres familias:

      A. Operaciones de sistema operativo: particiones, arranque, servicios, registro,
         cuentas locales, firewall, tareas programadas, ACLs, apagado/reinicio,
         elevacion, instalacion de software, ejecucion de codigo descargado.
      B. Borrado de ficheros fuera de las raices permitidas (por defecto Documents del
         usuario y el directorio temporal).
      C. Perdida irreversible de datos o de historial (force-push, prune de volumenes,
         DROP DATABASE...).

    Las tres familias exigen intervencion humana. Todo lo demas es trabajo normal de
    desarrollo y se aprueba solo.

    Dos modos de uso (parametro -Mode):

      PreToolUse         Se ejecuta ANTES de cada llamada. Si detecta riesgo devuelve
                         `permissionDecision: "ask"`. Si no, no escribe nada y el flujo
                         normal de permisos continua.
      PermissionRequest  Se ejecuta cuando Claude Code iba a mostrar un prompt de
                         permiso. Si NO hay riesgo devuelve `permissionDecision:
                         "allow"` (autonomia). Si hay riesgo no escribe nada y el
                         prompt se muestra al humano.

    Ambos modos comparten exactamente el mismo analisis, de forma que el auto-aprobador
    nunca puede aprobar algo que la guarda considera peligroso.

.NOTES
    Esta guarda nunca deniega de forma definitiva: eleva la decision al humano.
    Los bloqueos duros viven en `permissions.deny` de .claude/settings.json.
    Tests: .claude/hooks/test_guard_operaciones_riesgo.py
#>
[CmdletBinding()]
param(
    [ValidateSet('PreToolUse', 'PermissionRequest')]
    [string]$Mode = 'PreToolUse',

    # Raices donde el agente puede borrar sin pedir permiso.
    [string[]]$DeleteRoots = @()
)

$ErrorActionPreference = 'Stop'

if (-not $DeleteRoots -or $DeleteRoots.Count -eq 0) {
    $DeleteRoots = @(
        (Join-Path $env:USERPROFILE 'Documents'),
        $env:TEMP
    )
}

# ---------------------------------------------------------------- utilidades ---

function ConvertTo-WindowsPath {
    param([string]$Raw)

    if ([string]::IsNullOrWhiteSpace($Raw)) { return $null }

    $s = $Raw.Trim().Trim('"').Trim("'")
    if ([string]::IsNullOrWhiteSpace($s)) { return $null }

    if ($s.StartsWith('~')) { $s = $env:USERPROFILE + $s.Substring(1) }
    if ($s -match '^/mnt/([A-Za-z])/')          { $s = $s -replace '^/mnt/([A-Za-z])/', '$1:/' }
    elseif ($s -match '^/cygdrive/([A-Za-z])/') { $s = $s -replace '^/cygdrive/([A-Za-z])/', '$1:/' }
    elseif ($s -match '^/([A-Za-z])/')          { $s = $s -replace '^/([A-Za-z])/', '$1:/' }

    return ($s -replace '/', '\')
}

function Test-AbsolutePath {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { return $false }
    return ($Path -match '^[A-Za-z]:\\') -or ($Path -match '^\\\\')
}

function Test-UnderRoot {
    param([string]$Path, [string[]]$Roots)

    foreach ($root in $Roots) {
        $normalized = ConvertTo-WindowsPath $root
        if (-not $normalized) { continue }
        $normalized = $normalized.TrimEnd('\')
        if ($Path -ieq $normalized) { return $true }
        if ($Path.StartsWith($normalized + '\', [System.StringComparison]::OrdinalIgnoreCase)) { return $true }
    }
    return $false
}

# ------------------------------------------------------------------- entrada ---

$raw = [Console]::In.ReadToEnd()
if ([string]::IsNullOrWhiteSpace($raw)) { exit 0 }

try { $payload = $raw | ConvertFrom-Json } catch { exit 0 }

$command = $null
if ($payload.tool_input) { $command = $payload.tool_input.command }
if ([string]::IsNullOrWhiteSpace($command)) { exit 0 }

$cwd = $null
if ($payload.cwd) { $cwd = $payload.cwd }
if ([string]::IsNullOrWhiteSpace($cwd)) { $cwd = (Get-Location).Path }

# ------------------------------------------------------------------ analisis ---

# Posicion de comando: inicio de cadena, o tras ; | & ( o salto de linea.
$sep = '(?:^|[;&|(\r\n])\s*(?:sudo\s+)?'

# --- Familia A: operaciones de sistema operativo -------------------------------
$systemPatterns = [ordered]@{
    'particiones o formateo de disco' = @(
        '\bdiskpart\b', '\bfdisk\b', '\bmkfs(\.\w+)?\b', '\bchkdsk\b',
        'Format-Volume', 'Clear-Disk', 'Initialize-Disk', 'Remove-Partition',
        'Set-Partition', '\bcipher\s+/w', '\bdd\s+if=', ($sep + 'format\b')
    )
    'arranque del sistema' = @('\bbcdedit\b', '\bbcdboot\b', '\bbootrec\b')
    'apagado, reinicio o cierre de sesion' = @(
        '\bshutdown\b', '\blogoff\b', 'Restart-Computer', 'Stop-Computer'
    )
    'registro de Windows (escritura)' = @(
        '\breg(\.exe)?\s+(add|delete|import|load|unload|restore)\b',
        '(Set|New|Remove|Clear)-Item(Property)?[\s\S]{0,120}HK(LM|CU|CR|U)[:\\]',
        'reg(istry)?::HKEY'
    )
    'servicios de Windows' = @(
        '\bsc(\.exe)?\s+(create|delete|config|stop|start|failure)\b',
        'New-Service', 'Set-Service', 'Remove-Service', 'Stop-Service', 'Restart-Service'
    )
    'cuentas de usuario o grupos locales' = @(
        '\bnet(\.exe)?\s+(user|localgroup|group|share|accounts)\b',
        'New-LocalUser', 'Remove-LocalUser', 'Set-LocalUser',
        'Add-LocalGroupMember', 'Remove-LocalGroupMember'
    )
    'red o firewall del sistema' = @(
        '\bnetsh\b', 'New-NetFirewallRule', 'Set-NetFirewallRule',
        'Set-NetFirewallProfile', 'Disable-NetAdapter', 'Set-DnsClientServerAddress'
    )
    'politicas de seguridad o antivirus' = @(
        'Set-ExecutionPolicy', 'Set-MpPreference', 'Add-MpPreference',
        'Disable-WindowsOptionalFeature', 'Enable-WindowsOptionalFeature',
        '\bdism\b', ($sep + 'sfc\b'), '\bsecedit\b', '\bgpupdate\b'
    )
    'tareas programadas' = @(
        '\bschtasks\b', 'Register-ScheduledTask', 'Unregister-ScheduledTask',
        'New-ScheduledTask', 'Set-ScheduledTask'
    )
    'permisos o propiedad de ficheros del sistema' = @(
        '\btakeown\b', '\bicacls\b', '\bcacls\b', 'Set-Acl'
    )
    'instalacion de software en el sistema' = @(
        '\bmsiexec\b', '\bwinget\b', ($sep + 'choco\b'), ($sep + 'scoop\b'),
        'Install-WindowsFeature', 'Install-Module', 'Uninstall-Module', '\bwusa\b'
    )
    'elevacion de privilegios' = @(
        ($sep + 'runas\b'), 'Start-Process[\s\S]{0,120}-Verb\s+RunAs'
    )
    'ejecucion de codigo descargado de internet' = @(
        'Invoke-Expression', ($sep + 'iex\b'), 'DownloadString', 'DownloadFile',
        '(curl|wget|iwr|Invoke-WebRequest)[\s\S]{0,200}\|\s*(ba|z)?sh\b'
    )
    'borrado de registros de auditoria o copias de seguridad' = @(
        '\bvssadmin\b', '\bwevtutil\b', 'Clear-EventLog', 'Remove-EventLog', '\bwbadmin\b'
    )
    'parada de procesos criticos del sistema' = @(
        '(Stop-Process|taskkill)[\s\S]{0,160}\b(lsass|csrss|winlogon|smss|wininit|services)\b'
    )
    'consultas WMI administrativas' = @('\bwmic\b')
}

# --- Familia C: perdida irreversible de datos o historial -----------------------
$dataLossPatterns = [ordered]@{
    'reescritura del historial remoto de git' = @(
        'git[\s\S]{0,80}push[\s\S]{0,120}(--force(?!-with-lease)|(^|\s)-f(\s|$))',
        'git[\s\S]{0,80}(filter-branch|filter-repo)\b'
    )
    'borrado de volumenes o imagenes Docker' = @(
        'docker[\s\S]{0,40}system\s+prune',
        'docker[\s\S]{0,40}volume\s+(rm|prune)',
        'docker[\s\S]{0,40}image\s+prune[\s\S]{0,40}(-a|--all)'
    )
    'destruccion de esquema o datos en base de datos' = @(
        '\bDROP\s+(DATABASE|SCHEMA)\b', '\bTRUNCATE\s+TABLE\b',
        'alembic[\s\S]{0,60}downgrade\s+base'
    )
    'limpieza destructiva del arbol de trabajo' = @(
        'git\s+clean[\s\S]{0,40}-[a-z]*x[a-z]*d|git\s+clean[\s\S]{0,40}-[a-z]*d[a-z]*x'
    )
}

$riskReason = $null

foreach ($category in $systemPatterns.Keys) {
    foreach ($pattern in $systemPatterns[$category]) {
        if ([regex]::IsMatch($command, $pattern, 'IgnoreCase')) {
            $riskReason = "Operacion de sistema operativo ($category): requiere autorizacion humana explicita."
            break
        }
    }
    if ($riskReason) { break }
}

if (-not $riskReason) {
    foreach ($category in $dataLossPatterns.Keys) {
        foreach ($pattern in $dataLossPatterns[$category]) {
            if ([regex]::IsMatch($command, $pattern, 'IgnoreCase')) {
                $riskReason = "Perdida irreversible de datos o historial ($category): requiere autorizacion humana explicita."
                break
            }
        }
        if ($riskReason) { break }
    }
}

# --- Familia B: borrado fuera de las raices permitidas -------------------------
if (-not $riskReason) {
    $deletePattern = $sep + '(rm|rmdir|rd|del|erase|unlink|Remove-Item|ri|Clear-Content|Remove-ItemProperty)\b'
    $deleteAlt     = '\|\s*(Remove-Item|ri|rm)\b'
    $deleteFind    = '\bfind\b[\s\S]{0,200}(-delete|-exec\s+rm)\b'

    $isDeletion = [regex]::IsMatch($command, $deletePattern, 'IgnoreCase') -or
                  [regex]::IsMatch($command, $deleteAlt, 'IgnoreCase') -or
                  [regex]::IsMatch($command, $deleteFind, 'IgnoreCase')

    if ($isDeletion) {
        $tokens = [regex]::Matches($command, '"[^"]+"|''[^'']+''|[^\s;|&()]+') | ForEach-Object { $_.Value }

        foreach ($token in $tokens) {
            $clean = $token.Trim().Trim('"').Trim("'")
            if ([string]::IsNullOrWhiteSpace($clean)) { continue }

            # Flags de cmd/PowerShell (-rf, --force, /s, /q): no son rutas.
            if ($clean -match '^[-][-]?\w') { continue }
            if ($clean -match '^/\w{1,3}$') { continue }

            $looksAbsolute = $clean.StartsWith('~') -or $clean.StartsWith('/') -or
                             $clean.StartsWith('\\') -or ($clean -match '^[A-Za-z]:[\\/]')

            $normalized = ConvertTo-WindowsPath $clean
            if (-not $normalized) { continue }

            if ($looksAbsolute) {
                if (-not (Test-AbsolutePath $normalized)) {
                    $riskReason = "Borrado sobre una ruta raiz del sistema ('$clean'): requiere autorizacion humana explicita."
                    break
                }
                if (-not (Test-UnderRoot $normalized $DeleteRoots)) {
                    $riskReason = "Borrado fuera de las carpetas permitidas ('$clean'). Solo se autoborra dentro de: $($DeleteRoots -join '; ')."
                    break
                }
                continue
            }

            # Ruta relativa: solo importa si escapa de las raices permitidas via '..'.
            if ($normalized -notmatch '\.\.') { continue }
            try {
                $resolved = [System.IO.Path]::GetFullPath((Join-Path $cwd $normalized))
            } catch {
                continue
            }
            if (-not (Test-UnderRoot $resolved $DeleteRoots)) {
                $riskReason = "Borrado con ruta relativa que sale de las carpetas permitidas ('$clean' -> '$resolved'): requiere autorizacion humana explicita."
                break
            }
        }
    }
}

# ------------------------------------------------------------------- decision ---

function Write-Decision {
    param([string]$Event, [string]$Decision, [string]$Reason)

    $out = @{
        hookSpecificOutput = @{
            hookEventName            = $Event
            permissionDecision       = $Decision
            permissionDecisionReason = $Reason
        }
    }
    Write-Output ($out | ConvertTo-Json -Depth 5 -Compress)
}

if ($Mode -eq 'PreToolUse') {
    if ($riskReason) { Write-Decision 'PreToolUse' 'ask' $riskReason }
    exit 0
}

# Mode = PermissionRequest: autoaprueba lo que no es riesgo.
if (-not $riskReason) {
    Write-Decision 'PermissionRequest' 'allow' 'Operacion de desarrollo sin riesgo de sistema ni borrado externo: autoaprobada por la guarda agentica.'
}
exit 0
