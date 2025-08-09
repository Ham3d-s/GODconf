import re

def _beautify_name(name: str) -> str:
    """
    --- ENHANCEMENT ---
    نام‌ها را با جایگزینی '-' و '_' با فاصله، اعمال Title Case،
    و حذف فاصله‌های اضافی، زیباتر می‌کند.
    """
    # جایگزینی کاراکترهای جداکننده با فاصله
    name_with_spaces = name.replace('_', ' ').replace('-', ' ')
    # حذف فاصله‌های اضافی و تکراری
    normalized_spaces = re.sub(r'\s+', ' ', name_with_spaces).strip()
    return normalized_spaces.title()

def deep_merge(source: dict, destination: dict) -> dict:
    """دو دیکشنری را به صورت بازگشتی و عمیق ادغام می‌کند."""
    for key, value in source.items():
        if isinstance(value, dict) and key in destination and isinstance(destination[key], dict):
            deep_merge(value, destination[key])
        else:
            destination[key] = value
    return destination

def count_links(d: dict) -> int:
    """تعداد مقادیر نهایی (برگ‌ها) را در یک دیکشنری تو در تو می‌شمارد."""
    return sum(count_links(v) if isinstance(v, dict) else 1 for v in d.values())

def parse_github_url(repo_url: str) -> tuple[str | None, str | None]:
    """یک URL گیت‌هاب را تجزیه کرده و نام مالک و ریپازیتوری را برمی‌گرداند."""
    match = re.search(r"github\.com/([^/]+)/([^/]+)", repo_url)
    if match:
        owner, repo_name = match.groups()
        return owner, repo_name.replace('.git', '')
    return None, None
