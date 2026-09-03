"""CJK-aware tokenization for relevance scoring and near-duplicate detection.

The skill ships with zero hard dependencies (pyproject ``dependencies = []``)
so it installs across 50+ Agent Skills hosts as plain Python. Chinese text has
no whitespace word boundaries, so the original ``str.split()`` tokenizers in
relevance.py / dedupe.py collapse a whole sentence into a single token and
break token-overlap scoring and Jaccard de-duplication for Chinese sources
(Xiaohongshu, Bilibili).

``segment(text)`` fixes that. It splits text into maximal CJK and non-CJK runs:

- Non-CJK (ASCII / Latin) runs keep the original ``\\w+`` word behaviour.
- CJK runs are routed through jieba when it is installed (best quality), and
  fall back to character bigrams when jieba is absent. Bigrams are a
  dictionary-free segmentation that still gives robust overlap when a query
  appears inside a longer phrase.

jieba stays OPTIONAL: present -> used; absent -> bigram fallback. We never add
it to the hard dependency set, preserving the install-anywhere property.
"""

from __future__ import annotations

import re
from typing import List

# CJK ideographs + Japanese kana + Korean hangul. The Chinese ideograph block
# (\u4e00-\u9fff) and its extension-A (\u3400-\u4dbf) cover the cases we care
# about; kana/hangul are included so mixed-language text degrades gracefully.
_CJK_CHARS = r"\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3040-\u30ff\uac00-\ud7af"
_CJK_RE = re.compile(f"[{_CJK_CHARS}]")
_CJK_RUN_RE = re.compile(f"[{_CJK_CHARS}]+")
_LATIN_RE = re.compile(r"\w+")

# High-frequency Chinese function words that dilute overlap signal, mirroring
# the role of the English STOPWORDS sets in relevance.py / dedupe.py.
CHINESE_STOPWORDS = frozenset(
    {
        "\u7684", "\u4e86", "\u548c", "\u662f", "\u5728", "\u6211", "\u6709", "\u4e5f", "\u5c31", "\u4e0d", "\u4eba", "\u90fd",
        "\u4e00", "\u4e00\u4e2a", "\u4e0a", "\u5f88", "\u5230", "\u8bf4", "\u8981", "\u53bb", "\u4f60", "\u4f1a", "\u7740",
        "\u6ca1\u6709", "\u770b", "\u597d", "\u81ea\u5df1", "\u8fd9", "\u90a3", "\u8fd9\u4e2a", "\u90a3\u4e2a", "\u4ec0\u4e48", "\u600e\u4e48",
        "\u4e3a\u4ec0\u4e48", "\u4ee5\u53ca", "\u6216\u8005", "\u4f46\u662f", "\u56e0\u4e3a", "\u6240\u4ee5", "\u5982\u679c", "\u53ef\u4ee5",
        "\u8fd9\u6837", "\u90a3\u6837", "\u4ed6\u4eec", "\u6211\u4eec", "\u4f60\u4eec", "\u5b83", "\u5979", "\u4ed6", "\u5417", "\u5462",
        "\u5427", "\u554a", "\u54e6", "\u55ef", "\u4e0e", "\u53ca", "\u7b49", "\u88ab", "\u628a", "\u8ba9", "\u7ed9", "\u5411",
        "\u8fd8", "\u518d", "\u53c8", "\u4ece", "\u5bf9", "\u4e3a", "\u4ee5", "\u4e4b", "\u5176", "\u4e2d",
    }
)

# Optional jieba, resolved once at import time. Binding it here (rather than
# lazily on first use) avoids a race: the pipeline scores relevance inside a
# ThreadPoolExecutor, so a lazy initializer with mutable globals could have two
# threads import concurrently and observe a half-initialized state. Doing it at
# module load means the binding is settled before any worker thread runs.
#
# The BROAD `except Exception` is intentional: jieba is an optional enhancement,
# so ANY failure to load it — package absent, corrupted install, missing data
# files, or a setLogLevel signature change across versions — must degrade to the
# bigram fallback, never crash the skill. jieba guards its own first-call
# dictionary build with an internal lock, so concurrent `cut()` is safe once the
# module object is bound.
try:
    import jieba as _jieba  # type: ignore

    _jieba.setLogLevel(60)  # silence dictionary-build chatter on stderr
except Exception:
    _jieba = None


def has_cjk(text: str) -> bool:
    """True if the text contains any CJK / kana / hangul character."""
    return bool(text) and _CJK_RE.search(text) is not None


def _cjk_tokens(run: str) -> List[str]:
    # Reads the module-global _jieba at call time, so tests can force the bigram
    # path deterministically by setting cjk._jieba = None regardless of whether
    # jieba is installed in the environment.
    if _jieba is not None:
        return [w for w in _jieba.cut(run) if w.strip() and _CJK_RE.search(w)]
    # Dictionary-free fallback: character bigrams (single char if run length 1).
    if len(run) <= 1:
        return [run] if run else []
    return [run[i:i + 2] for i in range(len(run) - 1)]


def segment(text: str) -> List[str]:
    """Tokenize mixed CJK / Latin text into a flat list of lowercased tokens.

    CJK runs -> jieba words or character bigrams. Latin runs -> ``\\w+`` words.
    Order is preserved; callers that want a set can wrap the result.
    """
    if not text:
        return []
    text = text.lower()
    if not has_cjk(text):
        return _LATIN_RE.findall(text)

    out: List[str] = []
    pos = 0
    for match in _CJK_RUN_RE.finditer(text):
        if match.start() > pos:
            out.extend(_LATIN_RE.findall(text[pos:match.start()]))
        out.extend(_cjk_tokens(match.group()))
        pos = match.end()
    if pos < len(text):
        out.extend(_LATIN_RE.findall(text[pos:]))
    return out
