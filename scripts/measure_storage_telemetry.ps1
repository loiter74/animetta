param([string]$OutputPath,[string]$StopPath)
$timer = [Diagnostics.Stopwatch]::StartNew()
while (-not (Test-Path -LiteralPath $StopPath)) {
    $disks = @(Get-CimInstance Win32_PerfFormattedData_PerfDisk_PhysicalDisk | Select-Object Name,DiskReadBytesPersec,DiskWriteBytesPersec,PercentDiskTime,PercentIdleTime,CurrentDiskQueueLength,AvgDiskQueueLength)
    $cpu = Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor -Filter "Name='_Total'" | Select-Object PercentProcessorTime,PercentIdleTime
    @{utc=[DateTime]::UtcNow.ToString('o');monotonic_seconds=$timer.Elapsed.TotalSeconds;disks=$disks;cpu=$cpu} | ConvertTo-Json -Compress -Depth 5 | Add-Content -LiteralPath $OutputPath -Encoding utf8
    Start-Sleep -Seconds 2
}
