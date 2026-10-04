# PSScriptAnalyzer settings for Collect-AgentArtifacts.ps1 and tests/smoke.ps1.
# Run from the repository root with PSScriptAnalyzer 1.25.0:
#   Invoke-ScriptAnalyzer -Path collectors/Collect-AgentArtifacts.ps1 -Settings collectors/PSScriptAnalyzerSettings.psd1
#
# The default rule set at Error and Warning severity, plus the compatibility
# rules, which machine-check the "Windows PowerShell 5.1, not PowerShell 7"
# standard in AGENTS.md.
@{
    Severity     = @('Error', 'Warning')
    IncludeDefaultRules = $true

    ExcludeRules = @(
        # Every function in the collector is an internal helper of a single
        # non-interactive script run once from an EDR console; the plural
        # nouns (Get-Homes, Expand-CatalogEntries, ...) describe what each
        # returns, and renaming them would add churn with no behaviour change.
        'PSUseSingularNouns',
        # Each empty catch is a best-effort probe whose failure is the
        # expected case and already accounted for: a size or attribute left
        # at its default, an unreadable project-discovery file skipped, the
        # staging cleanup after the archive is written. They mirror the sh
        # collector's `2>/dev/null || :`; logging them would flood the log
        # on every host without telling the responder anything.
        'PSAvoidUsingEmptyCatchBlock'
    )

    Rules = @{
        PSUseCompatibleSyntax = @{
            Enable         = $true
            TargetVersions = @('5.1', '7.4')
        }
        # Profile names are the files PSScriptAnalyzer 1.25.0 ships under
        # compatibility_profiles/:
        #   win-8_x64_10.0.14393.0_5.1.14393.2791_x64_4.0.30319.42000_framework
        #     Windows Server 2016, Windows PowerShell 5.1
        #   win-48_x64_10.0.17763.0_5.1.17763.316_x64_4.0.30319.42000_framework
        #     Windows 10 (1809), Windows PowerShell 5.1
        PSUseCompatibleCommands = @{
            Enable         = $true
            TargetProfiles = @(
                'win-8_x64_10.0.14393.0_5.1.14393.2791_x64_4.0.30319.42000_framework',
                'win-48_x64_10.0.17763.0_5.1.17763.316_x64_4.0.30319.42000_framework'
            )
        }
        PSUseCompatibleTypes = @{
            Enable         = $true
            TargetProfiles = @(
                'win-8_x64_10.0.14393.0_5.1.14393.2791_x64_4.0.30319.42000_framework',
                'win-48_x64_10.0.17763.0_5.1.17763.316_x64_4.0.30319.42000_framework'
            )
            # Not loaded by default on Server 2016, so both scripts run
            # `Add-Type -AssemblyName System.IO.Compression.FileSystem` before
            # touching it; the rule cannot see that.
            IgnoreTypes    = @('System.IO.Compression.ZipFile')
        }
        PSUseCompatibleCmdlets = @{
            Compatibility = @('desktop-5.1.14393.206-windows')
        }
    }
}
