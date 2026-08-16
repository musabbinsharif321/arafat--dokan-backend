from decimal import Decimal
import json
from .models import Product, TransactionItem

def recalculate_product_stock_and_cost(product_or_id):
    """
    Chronologically recalculates stock and weighted average purchase price
    for a given product from all its historical transactions.
    """
    if not product_or_id:
        return None
    
    if isinstance(product_or_id, (int, str)):
        try:
            product = Product.objects.get(id=int(product_or_id))
        except (Product.DoesNotExist, ValueError):
            return None
    else:
        product = product_or_id

    items = (
        TransactionItem.objects
        .filter(product=product)
        .select_related('transaction')
        .order_by('transaction__created_at', 'transaction__id', 'id')
    )

    if not items.exists():
        product.stock = 0.0
        product.purchase_price = 0.0
        product.save(update_fields=['stock', 'purchase_price'])
        return product

    running_stock = 0.0
    running_purchase_price = 0.0

    for item in items:
        tx = item.transaction
        if not tx:
            continue
        
        tx_type = tx.transaction_type
        qty = float(item.quantity or 0)
        unit_price = float(item.price or 0)

        if tx_type == 'purchase':
            # Extract landed cost (shipping + labor from notes)
            extra_per_unit = 0.0
            if tx.notes and tx.notes.strip().startswith('{'):
                try:
                    first_line = tx.notes.split('\n')[0]
                    meta = json.loads(first_line)
                    ship = float(meta.get('shippingCost') or 0.0)
                    lab = float(meta.get('laborCost') or 0.0)
                    tot_extra = ship + lab
                    tot_qty = sum(float(it.quantity or 0) for it in tx.items.all())
                    if tot_qty > 0 and tot_extra > 0:
                        extra_per_unit = tot_extra / tot_qty
                except Exception:
                    pass

            landed_price = unit_price + extra_per_unit

            if (running_stock + qty) > 0 and running_stock > 0 and running_purchase_price > 0:
                running_purchase_price = ((running_stock * running_purchase_price) + (qty * landed_price)) / (running_stock + qty)
            elif landed_price > 0:
                running_purchase_price = landed_price

            running_stock += qty

        elif tx_type == 'sale':
            running_stock = max(0.0, running_stock - qty)

        elif tx_type == 'sale_return':
            running_stock += qty

        elif tx_type == 'purchase_return':
            running_stock = max(0.0, running_stock - qty)

    product.stock = Decimal(str(round(running_stock, 2)))
    if running_purchase_price > 0:
        product.purchase_price = Decimal(str(round(running_purchase_price, 2)))
    product.save(update_fields=['stock', 'purchase_price'])
    return product


def generate_product_cost_log(product_or_id):
    """
    Generates a full chronological step-by-step history log for a product,
    showing every invoice, quantity change, rate, and weighted cost calculation formula.
    """
    if not product_or_id:
        return None
    
    if isinstance(product_or_id, (int, str)):
        try:
            product = Product.objects.get(id=int(product_or_id))
        except (Product.DoesNotExist, ValueError):
            return None
    else:
        product = product_or_id

    items = (
        TransactionItem.objects
        .filter(product=product)
        .select_related('transaction', 'transaction__party')
        .order_by('transaction__created_at', 'transaction__id', 'id')
    )

    items_list = list(items)
    logs = []
    running_stock = 0.0
    running_purchase_price = 0.0
    any_prior_edited = False

    for idx, item in enumerate(items_list):
        tx = item.transaction
        if not tx:
            continue
        
        tx_type = tx.transaction_type
        qty = float(item.quantity or 0)
        unit_price = float(item.price or 0)
        stock_before = running_stock
        cost_before = running_purchase_price

        formula = ""
        extra_per_unit = 0.0

        if tx_type == 'purchase':
            if tx.notes and tx.notes.strip().startswith('{'):
                try:
                    first_line = tx.notes.split('\n')[0]
                    meta = json.loads(first_line)
                    ship = float(meta.get('shippingCost') or 0.0)
                    lab = float(meta.get('laborCost') or 0.0)
                    tot_extra = ship + lab
                    tot_qty = sum(float(it.quantity or 0) for it in tx.items.all())
                    if tot_qty > 0 and tot_extra > 0:
                        extra_per_unit = tot_extra / tot_qty
                except Exception:
                    pass

            landed_price = unit_price + extra_per_unit

            if (running_stock + qty) > 0 and running_stock > 0 and running_purchase_price > 0:
                new_price = ((running_stock * running_purchase_price) + (qty * landed_price)) / (running_stock + qty)
                formula = f"(({round(running_stock, 2)} × ৳{round(running_purchase_price, 2)}) + ({round(qty, 2)} × ৳{round(landed_price, 2)})) / {round(running_stock + qty, 2)} = ৳{round(new_price, 2)}"
                running_purchase_price = new_price
            elif landed_price > 0:
                running_purchase_price = landed_price
                formula = f"নতুন রেট: ৳{round(landed_price, 2)}"

            running_stock += qty

        elif tx_type == 'sale':
            running_stock = max(0.0, running_stock - qty)
            formula = f"বিক্রি: -{round(qty, 2)} {product.unit} (ক্রয়মূল্য অপরিবর্তিত ৳{round(running_purchase_price, 2)})"

        elif tx_type == 'sale_return':
            running_stock += qty
            formula = f"বিক্রয় ফেরত: +{round(qty, 2)} {product.unit} (ক্রয়মূল্য ৳{round(running_purchase_price, 2)})"

        elif tx_type == 'purchase_return':
            running_stock = max(0.0, running_stock - qty)
            formula = f"ক্রয় ফেরত: -{round(qty, 2)} {product.unit} (ক্রয়মূল্য ৳{round(running_purchase_price, 2)})"

        party_name = tx.party_name or (tx.party.name if tx.party else '')
        
        type_labels = {
            'purchase': 'ক্রয় (Purchase)',
            'sale': 'বিক্রয় (Sale)',
            'sale_return': 'বিক্রয় ফেরত (Sale Return)',
            'purchase_return': 'ক্রয় ফেরত (Purchase Return)',
            'payment_in': 'পেমেন্ট গ্রহণ',
            'payment_out': 'পেমেন্ট প্রদান'
        }

        # Check if transaction was edited/updated after its creation
        is_edited = False
        edit_date_str = ""
        subsequent_purchases_count = 0
        subsequent_total_count = 0
        recalc_reason = ""

        if tx.updated_at and tx.created_at:
            time_diff = (tx.updated_at - tx.created_at).total_seconds()
            if time_diff > 10:  # edited more than 10s after initial creation
                is_edited = True
                any_prior_edited = True
                edit_date_str = tx.updated_at.strftime('%d/%m/%Y %I:%M %p')
                subsequent_items = items_list[idx + 1:]
                subsequent_purchases_count = sum(1 for it in subsequent_items if it.transaction and it.transaction.transaction_type == 'purchase')
                subsequent_total_count = len(subsequent_items)
                recalc_reason = "চালানটিতে পণ্য বা পরিমাণ সংশোধন করায় পূর্ববর্তী স্টক পরিবর্তিত হয়েছিল।"

        logs.append({
            'transaction_id': tx.id,
            'invoice_no': tx.invoice_no,
            'date': tx.created_at.strftime('%d/%m/%Y %I:%M %p') if tx.created_at else '',
            'raw_date': tx.created_at.isoformat() if tx.created_at else '',
            'is_edited': is_edited,
            'edited_at': edit_date_str,
            'recalculation_reason': recalc_reason,
            'subsequent_purchases_recalculated': subsequent_purchases_count,
            'subsequent_transactions_recalculated': subsequent_total_count,
            'was_recomputed_due_to_prior_edit': (not is_edited) and any_prior_edited,
            'transaction_type': tx_type,
            'transaction_type_label': type_labels.get(tx_type, tx_type),
            'party_name': party_name,
            'quantity': qty,
            'unit': product.unit,
            'rate': unit_price,
            'extra_per_unit': round(extra_per_unit, 2),
            'landed_cost': round(unit_price + extra_per_unit, 2),
            'stock_before': round(stock_before, 2),
            'stock_after': round(running_stock, 2),
            'cost_before': round(cost_before, 2),
            'cost_after': round(running_purchase_price, 2),
            'cost_change': round(running_purchase_price - cost_before, 2),
            'formula': formula
        })

    has_recalculations = any(l['is_edited'] for l in logs)
    latest_recalc_date = max([l['edited_at'] for l in logs if l['is_edited']], default="")

    return {
        'product_id': product.id,
        'product_name': product.name,
        'unit': product.unit,
        'current_stock': float(product.stock),
        'current_purchase_price': float(product.purchase_price),
        'has_recalculations': has_recalculations,
        'latest_recalculation_date': latest_recalc_date,
        'logs': logs[::-1]  # Latest first
    }
