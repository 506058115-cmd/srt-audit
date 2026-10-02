# srt-audit

Check a SubRip (`.srt`) file for malformed timestamps, invalid cue ranges, duplicate cue numbers, out-of-order starts, and overlaps. It reports line numbers and fixed issue descriptions only; subtitle text is never printed.

## Use

Requires Python 3.10+; no packages to install.

```sh
python srt_audit.py movie.srt
cat movie.srt | python srt_audit.py -
```

The input is limited to 32 MiB and must be UTF-8 (an optional UTF-8 BOM is accepted). Blank lines separate cue blocks. Cue numbers are optional; each block must contain a SubRip timestamp line. Any reported issue exits with status 1; an unreadable, oversized, or invalidly encoded input exits with status 2.

Overlap and ordering checks are structural hints, not a judgement about subtitle quality. This tool does not validate subtitle text, speaker labels, styling, or synchronization against media.

## License

MIT
