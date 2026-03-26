from __future__ import annotations

BRAND_OPTIONS = [
    "Sekolah Seller",
    "Akademi Profit",
    "Berani Export Import",
]

MEMBER_PRODUCT_KEYWORDS = ("member platinum", "paket platinum", "platinum", "member ")
FOLLOWUP_PRODUCT_KEYWORDS = ("zoom", "webinar")


def _normalized_text(*values: str | None) -> str:
    return " ".join(str(value or "").strip().lower() for value in values if str(value or "").strip())


def detect_brand(product: str = "", product_code: str = "", source_file: str = "") -> str:
    text = _normalized_text(product, product_code, source_file)
    if "akademi profit" in text:
        return "Akademi Profit"
    if "berani export import" in text or "export import" in text:
        return "Berani Export Import"
    if "sekolah seller" in text or "seller" in text:
        return "Sekolah Seller"
    return "Umum"


def classify_funnel(product: str = "", product_code: str = "", source_file: str = "") -> str:
    text = _normalized_text(product, product_code, source_file)
    if any(keyword in text for keyword in MEMBER_PRODUCT_KEYWORDS):
        return "member"
    if any(keyword in text for keyword in FOLLOWUP_PRODUCT_KEYWORDS):
        return "zoom_awal"
    return "lainnya"


def is_member_product(product: str = "", product_code: str = "", source_file: str = "") -> bool:
    return classify_funnel(product, product_code, source_file) == "member"


def is_followup_product(product: str = "", product_code: str = "", source_file: str = "") -> bool:
    return classify_funnel(product, product_code, source_file) == "zoom_awal"
