from __future__ import annotations

from typing import Final

from airflow_lite.i18n.translations_en import EN
from airflow_lite.i18n.translations_ko import KO

DEFAULT_LANGUAGE: Final[str] = "en"
SUPPORTED_LANGUAGES: Final[frozenset[str]] = frozenset({"en", "ko"})

_TRANSLATIONS: Final[dict[str, dict[str, str]]] = {
    "en": EN,
    "ko": KO,
}


def normalize_language(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = str(value).strip().lower()
    if not candidate:
        return None
    candidate = candidate.replace("_", "-")
    primary = candidate.split("-", maxsplit=1)[0]
    if primary in SUPPORTED_LANGUAGES:
        return primary
    return None


def parse_accept_language(value: str | None) -> str | None:
    if not value:
        return None

    best_language: str | None = None
    best_quality = -1.0
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        parts = [segment.strip() for segment in item.split(";")]
        language = normalize_language(parts[0])
        if language is None:
            continue

        quality = 1.0
        for parameter in parts[1:]:
            if not parameter.startswith("q="):
                continue
            try:
                quality = float(parameter[2:])
            except ValueError:
                quality = 0.0
        if quality > best_quality:
            best_quality = quality
            best_language = language
    return best_language


def resolve_language(
    *,
    query_language: str | None = None,
    default_language: str | None = None,
    accept_language: str | None = None,
) -> str:
    for candidate in (
        query_language,
        default_language,
        parse_accept_language(accept_language),
    ):
        normalized = normalize_language(candidate)
        if normalized:
            return normalized
    return DEFAULT_LANGUAGE


def require_supported_language(value: str, *, field_name: str) -> str:
    normalized = normalize_language(value)
    if normalized is None:
        supported = ", ".join(sorted(SUPPORTED_LANGUAGES))
        raise ValueError(
            f"지원되지 않는 언어 값입니다 ({field_name}): {value!r}. 지원값: {supported}"
        )
    return normalized


def translate(key: str, language: str, **kwargs) -> str:
    normalized = normalize_language(language) or DEFAULT_LANGUAGE
    message = _TRANSLATIONS.get(normalized, {}).get(key)
    if message is None:
        message = _TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key)
    if kwargs:
        return message.format(**kwargs)
    return message


__all__ = [
    "DEFAULT_LANGUAGE",
    "SUPPORTED_LANGUAGES",
    "normalize_language",
    "parse_accept_language",
    "resolve_language",
    "require_supported_language",
    "translate",
]
