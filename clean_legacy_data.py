import os
import re
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dokan_backend.settings')
django.setup()

from api.models import TransactionItem, Product, Transaction

def clean_legacy_name(name: str) -> str:
    if not name:
        return name
    s = name.strip()

    # Specific compound replacements
    replacements = [
        (r'10\s*wg[:.]\s*wj\s+Gm\s+wm\s+Avi\s+Gg\s+iW', '10 মি.মি এসসিআরএম রড'),
        (r'12\s*wg[:.]\s*wj\s+Gm\s+wm\s+Avi\s+Gg\s+iW', '12 মি.মি এসসিআরএম রড'),
        (r'16\s*wg[:.]\s*wj\s+Gm\s+wm\s+Avi\s+Gg\s+iW', '16 মি.মি এসসিআরএম রড'),
        (r'20\s*wg[:.]\s*wj\s+Gm\s+wm\s+Avi\s+Gg\s+iW', '20 মি.মি এসসিআরএম রড'),
        (r'22\s*wg[:.]\s*wj\s+Gm\s+wm\s+Avi\s+Gg\s+iW', '22 মি.মি এসসিআরএম রড'),
        (r'25\s*wg[:.]\s*wj\s+Gm\s+wm\s+Avi\s+Gg\s+iW', '25 মি.মি এসসিআরএম রড'),
        (r'8\s*wg[:.]\s*wj\s+Gm\s+wm\s+Avi\s+Gg\s+iW', '8 মি.মি এসসিআরএম রড'),

        (r'10\s*wg[:.]\s*wj\s+(?:we|G)\s+Gm\s+Avi\s+Gg\s+iW', '10 মি.মি বিএসআরএম রড'),
        (r'12\s*wg[:.]\s*wj\s+(?:we|G)\s+Gm\s+Avi\s+Gg\s+iW', '12 মি.মি বিএসআরএম রড'),
        (r'16\s*wg[:.]\s*wj\s+(?:we|G)\s+Gm\s+Avi\s+Gg\s+iW', '16 মি.মি বিএসআরএম রড'),
        (r'20\s*wg[:.]\s*wj\s+(?:we|G)\s+Gm\s+Avi\s+Gg\s+iW', '20 মি.মি বিএসআরএম রড'),
        (r'22\s*wg[:.]\s*wj\s+(?:we|G)\s+Gm\s+Avi\s+Gg\s+iW', '22 মি.মি বিএসআরএম রড'),
        (r'25\s*wg[:.]\s*wj\s+(?:we|G)\s+Gm\s+Avi\s+Gg\s+iW', '25 মি.মি বিএসআরএম রড'),
        (r'8\s*wg[:.]\s*wj\s+(?:we|G)\s+Gm\s+Avi\s+Gg\s+iW', '8 মি.মি বিএসআরএম রড'),

        (r'G¨vsKi\s+wm‡g›U', 'অ্যাংকর সিমেন্ট'),
        (r'†nvjwmg\s+wm‡g›U', 'হোলসিম সিমেন্ট'),
    ]

    for pat, rep in replacements:
        s = re.sub(pat, rep, s, flags=re.IGNORECASE)

    # Case-insensitive brand replacements
    ci_tokens = [
        (r'Gm\s+wm\s+Avi\s+Gg', 'এসসিআরএম'),
        (r'we\s+Gm\s+Avi\s+Gg', 'বিএসআরএম'),
        (r'G\s+Gm\s+Avi\s+Gg', 'বিএসআরএম'),
        (r'wg[:.]\s*wj', 'মি.মি'),
    ]
    for pat, rep in ci_tokens:
        s = re.sub(pat, rep, s, flags=re.IGNORECASE)

    # Exact case-sensitive Sutonny token replacements
    cs_tokens = [
        (r'iW', 'রড'),
        (r'‡K\s+Gm\s+Gg\s+Gj', 'কেএসএমএল'),
        (r'Av‡bvqvi', 'আনোয়ার'),
        (r'G‡KGm', 'একেএস'),
        (r'G¨vsKi', 'অ্যাংকর'),
        (r'†nvjwmg', 'হোলসিম'),
        (r'wm‡g›U', 'সিমেন্ট'),
        (r'†d«m', 'ফ্রেশ'),
    ]
    for pat, rep in cs_tokens:
        s = re.sub(pat, rep, s)

    return re.sub(r'\s+', ' ', s).strip()

def run_cleanup():
    print("Starting legacy text cleanup in database...")
    
    # 1. TransactionItems
    items_cleaned = 0
    for it in TransactionItem.objects.all():
        cleaned = clean_legacy_name(it.product_name)
        if cleaned != it.product_name:
            print(f"TransactionItem {it.id}: '{it.product_name}' -> '{cleaned}'")
            it.product_name = cleaned
            it.save(update_fields=['product_name'])
            items_cleaned += 1

    # 2. Products
    products_cleaned = 0
    for p in Product.objects.all():
        cleaned = clean_legacy_name(p.name)
        if cleaned != p.name:
            print(f"Product {p.id}: '{p.name}' -> '{cleaned}'")
            p.name = cleaned
            p.save(update_fields=['name'])
            products_cleaned += 1

    print(f"\nDone! Cleaned {items_cleaned} TransactionItems and {products_cleaned} Products.")

if __name__ == '__main__':
    run_cleanup()
