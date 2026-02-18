# SHA256 Checksum Verification

## v0.1.0-beta.1 Release (2026-02-04)

Use these checksums to verify the integrity of downloaded release files.

### How to Verify

**Windows PowerShell:**
```powershell
(Get-FileHash -Path "v0.1.0-beta.1.zip" -Algorithm SHA256).Hash
```

**Linux/macOS:**
```bash
sha256sum v0.1.0-beta.1.zip
```

### Checksums

To be generated during release process:

```
# Format: SHA256  Filename

[SHA256-Hash]  v0.1.0-beta.1.zip
[SHA256-Hash]  v0.1.0-beta.1.tar.gz
```

### Generate Checksums (For Maintainers)

**Windows PowerShell:**
```powershell
# Generate checksum for file
$hash = (Get-FileHash -Path "v0.1.0-beta.1.zip" -Algorithm SHA256).Hash
Write-Host "$hash  v0.1.0-beta.1.zip"

# Save to file
Get-FileHash -Path "v0.1.0-beta.1.zip" -Algorithm SHA256 | 
    ForEach-Object { "$($_.Hash)  v0.1.0-beta.1.zip" } | 
    Out-File -FilePath "CHECKSUM.txt"
```

**Linux/macOS:**
```bash
# Generate checksums for all release files
sha256sum v0.1.0-beta.1.zip v0.1.0-beta.1.tar.gz > CHECKSUM.txt

# Verify checksums
sha256sum -c CHECKSUM.txt
```

### GPG Signature (Optional - Future Enhancement)

For enhanced security, releases may be signed with GPG:

```bash
gpg --detach-sign v0.1.0-beta.1.zip
gpg --verify v0.1.0-beta.1.zip.sig v0.1.0-beta.1.zip
```

---

**Note:** Checksums should be published alongside release artifacts on GitHub Releases page.
