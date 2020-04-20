Start-Transcript -Path "C:\first_boot.txt"

Get-ChildItem Env: | Out-File "C:\install_env.txt"

# DisableIndexing: Disable indexing on all disk volumes (for performance)
Get-WmiObject Win32_Volume -Filter "IndexingEnabled=$true" | Set-WmiInstance -Arguments @{IndexingEnabled=$false}

# Disable Windows Defender
# https://docs.microsoft.com/en-us/windows/security/threat-protection/windows-defender-antivirus/windows-defender-antivirus-on-windows-server-2016#install-or-uninstall-windows-defender-av-on-windows-server-2016
Uninstall-WindowsFeature -Name Windows-Defender

# use TLS 1.2 (see bug 1443595)
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# For making http requests
$client = New-Object system.net.WebClient
$shell = new-object -com shell.application

# Download a zip file and extract it
function Expand-ZIPFile($file, $destination, $url)
{
    $client.DownloadFile($url, $file)
    $zip = $shell.NameSpace($file)
    foreach($item in $zip.items())
    {
        $shell.Namespace($destination).copyhere($item)
    }
}

# Open up firewall for livelog (both PUT and GET interfaces)
New-NetFirewallRule -DisplayName "Allow livelog PUT requests" `
    -Direction Inbound -LocalPort 60022 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "Allow livelog GET requests" `
    -Direction Inbound -LocalPort 60023 -Protocol TCP -Action Allow

# Install generic-worker and dependencies
md C:\generic-worker
$client.DownloadFile("https://github.com/taskcluster/generic-worker/releases/download" +
    "/v16.5.5/generic-worker-multiuser-windows-amd64.exe", "C:\generic-worker\generic-worker.exe")
$client.DownloadFile("https://github.com/taskcluster/livelog/releases/download" +
    "/v1.1.0/livelog-windows-amd64.exe", "C:\generic-worker\livelog.exe")
$client.DownloadFile("https://github.com/taskcluster/taskcluster-proxy/releases/download" +
    "/v5.1.0/taskcluster-proxy-windows-amd64.exe", "C:\generic-worker\taskcluster-proxy.exe")
Expand-ZIPFile -File "C:\nssm-2.24.zip" -Destination "C:\" `
    -Url "https://www.nssm.cc/release/nssm-2.24.zip"
Start-Process C:\generic-worker\generic-worker.exe -ArgumentList `
    "new-ed25519-keypair --file C:\generic-worker\generic-worker-ed25519-signing-key.key" `
    -Wait -NoNewWindow -PassThru `
    -RedirectStandardOutput C:\generic-worker\generate-ed25519-signing-key.log `
    -RedirectStandardError C:\generic-worker\generate-ed25519-signing-key.err
Start-Process C:\generic-worker\generic-worker.exe -ArgumentList (
        "install service --nssm C:\nssm-2.24\win64\nssm.exe " +
        "--configure-for-aws " +
        "--config C:\generic-worker\generic-worker.config"
    ) -Wait -NoNewWindow -PassThru `
    -RedirectStandardOutput C:\generic-worker\install.log `
    -RedirectStandardError C:\generic-worker\install.err

# # For debugging, let us know the worker’s IP address through:
# # ssh servo-master.servo.org tail -f /var/log/nginx/access.log | grep ping
# Start-Process C:\nssm-2.24\win64\nssm.exe -ArgumentList `
#     "install", "servo-ping", "powershell", "-Command", @"
#     (New-Object system.net.WebClient).DownloadData(
#         'http://servo-master.servo.org/ping/generic-worker')
# "@

# # This "service" isn’t a long-running service: it runs once on boot and then terminates.
# Start-Process C:\nssm-2.24\win64\nssm.exe -ArgumentList `
#     "set", "servo-ping", "AppExit", "Default", "Exit"

Expand-ZIPFile -File "C:\depends22_x86.zip" -Destination "C:\" `
    -Url "http://www.dependencywalker.com/depends22_x86.zip"

# Visual C++ Build Tools
# https://blogs.msdn.microsoft.com/vcblog/2016/11/16/introducing-the-visual-studio-build-tools/
$client.DownloadFile("https://aka.ms/vs/16/release/vs_buildtools.exe", "C:\vs_buildtools.exe")
Start-Process C:\vs_buildtools.exe -ArgumentList (`
        "--passive --norestart --includeRecommended " +
        "--add Microsoft.VisualStudio.Workload.VCTools " +
        "--add Microsoft.VisualStudio.Workload.UniversalBuildTools " +
        "--add Microsoft.VisualStudio.Workload.MSBuildTools " +
        "--add Microsoft.VisualStudio.ComponentGroup.UWP.BuildTools " +
        "--add Microsoft.VisualStudio.ComponentGroup.UWP.VC.BuildTools " +
        "--add Microsoft.VisualStudio.Component.NuGet.BuildTools " +
        "--add Microsoft.VisualStudio.Component.VC.CLI.Support " +
        "--add Microsoft.VisualStudio.Component.VC.Tools.ARM64 " +
        "--add Microsoft.VisualStudio.Component.VC.ATL " +
        "--add Microsoft.VisualStudio.Component.VC.ATL.ARM64 " +
        "--add Microsoft.VisualStudio.Component.VC.ATLMFC " +
        "--add Microsoft.VisualStudio.Component.VC.MFC.ARM64 " +
        "--add Microsoft.VisualStudio.Component.Windows10SDK.18362 " +
        "--add Microsoft.VisualStudio.Component.Windows10SDK.17763 " +
        "--add Microsoft.VisualStudio.Component.Windows10SDK.17134"
    ) -Wait

reg add "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock" /t REG_DWORD /f /v "AllowDevelopmentWithoutDevLicense" /d "1"
reg add "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock" /t REG_DWORD /f /v "AllowAllTrustedApps" /d "1"

# Install the root certificate used for signing our UWP builds.
# Having them system-wide is necessary for running such builds.
# See https://github.com/servo/servo/pull/25661
$pfx = "REPLACE THIS WITH BASE64 PFX CODESIGN CERTIFICATE"
[IO.File]::WriteAllBytes("C:\servo.pfx", [System.Convert]::FromBase64String($pfx))
Import-PfxCertificate -FilePath C:\servo.pfx -CertStoreLocation Cert:\LocalMachine\Root
Remove-Item C:\servo.pfx

# Now shutdown, in preparation for creating an image
shutdown -s
