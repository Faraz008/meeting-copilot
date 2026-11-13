# Real Transcript Dataset

## AMI Meeting Corpus

The real transcript subset is derived from the **AMI Meeting Corpus**, using the manual annotation data distributed through the official AMI download page.

- Source: https://groups.inf.ed.ac.uk/ami/download/
- License: Creative Commons Attribution 4.0 International (CC BY 4.0)
- License URL: https://creativecommons.org/licenses/by/4.0/
- Corpus citation:

  Carletta, J. et al. (2006). *The AMI Meeting Corpus: A Pre-announcement.* Machine Learning for Multimodal Interaction (MLMI 2005), LNCS 3869, pp. 28–39. https://doi.org/10.1007/11677482_3

### Release provenance

The supplied source archive was named `ami_public_manual_1.6.2.zip`, while its internal `00README_MANUAL.txt` identifies the annotation data as **AMI Manual Annotations release 1.7**, dated 16 June 2014.

This discrepancy is retained explicitly. The internal release documentation identifies version 1.7; the archive filename suggests 1.6.2. The exact release designation has not been independently reconciled.

### Selection

Ten meetings categorized as `nonscenario` in the AMI corpus metadata were selected.

Each transcript contains the first 100 chronological annotated segments. These are excerpts, not complete meetings.

Original meeting IDs and speaker channel letters are preserved. Available annotation timestamps are retained in seconds. Meeting dates are taken from corpus metadata.

### Transformations

The original NXT annotations reference word ranges in corresponding word files. The following transformations were applied:

1. Resolved segment-to-word references.
2. Joined word tokens into segment-level text.
3. Preserved punctuation and available vocal-sound/disfluency markers.
4. Sorted segments by annotation start time.
5. Normalized the data into the project's transcript JSON schema.
6. Retained original meeting IDs, speaker letters, dates, and available timestamps.

No audio or video files are included.

### Selected meetings

| Meeting ID | Date | Turns |
|---|---|---:|
| EN2005a | 2005-04-29 | 100 |
| EN2009d | 2005-11-07 | 100 |
| EN2001a | 2005-02-08 | 100 |
| EN2001e | 2005-03-08 | 100 |
| IN1014 | 2005-10-11 | 100 |
| IN1016 | 2005-10-11 | 100 |
| EN2001d | 2005-03-01 | 100 |
| EN2006a | 2005-05-05 | 100 |
| IN1001 | 2005-10-03 | 100 |
| EN2001b | 2005-02-15 | 100 |

### Limitations

- These are excerpts, not full meetings.
- `nonscenario` is a corpus metadata category; it does not guarantee that every interaction represents an ordinary modern workplace meeting.
- Speaker letters are retained as corpus identifiers. They should not be interpreted as real participant names.
- The excerpts are suitable for transcript-processing and annotation experiments, but their limited length should be considered when evaluating extraction quality.

### Attribution and modifications

This dataset contains modified excerpts from the AMI Meeting Corpus. The source corpus is attributed above and licensed under CC BY 4.0.

Modifications include selecting the first 100 chronological annotated segments from each selected meeting, resolving NXT segment-to-word references, joining word tokens, and converting the result into the project's JSON schema.

The original corpus license and source attribution must be retained when redistributing these transcripts.
