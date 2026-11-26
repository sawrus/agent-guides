"""wordfreq: count word frequencies."""
import re
from collections import Counter

WORD = re.compile(r'\w+')


def count_words(text):
    """Counter of lower-cased words (letters, digits, underscore)."""
    return Counter(WORD.findall(text.lower()))


def top(text, n=10):
    """The n most common words as (word, count): count descending, then word ascending."""
    counts = count_words(text)
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:n]
