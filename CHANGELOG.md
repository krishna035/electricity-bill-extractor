# Changelog

## 2026-08-21

### Added
- Added validation for mismatches between calculated adjustments and bill-printed adjustments.
- Added regression coverage for Torrent payable amounts and UGVCL S-21 solar adjustments.

### Fixed
- Fixed Torrent payable totals to retain the precise amount due from the bill.
- Fixed consumption-demand unit rate calculations to exclude demand charges.
- Fixed UGVCL S-21 solar setoff, surplus, and banking adjustment extraction.
