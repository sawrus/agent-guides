# wordfreq spec

`python3 -m wordfreq [-n N] [FILE]` prints the N most common words (default 10), one `word count` per line.

Acceptance criteria:
1. Words are `\w+` sequences, compared in lower case.
2. Order: count descending, then word ascending.
3. Reads stdin when FILE is omitted.
