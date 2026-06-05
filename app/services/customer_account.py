"""Customer advance / ledger calculations.

A buyer can pay an advance (or part-payments). Each sale bills against that
balance. Remaining = total received - total billed:
  * positive  -> advance still available (credit)
  * negative  -> amount due from the customer
"""
from app import db
from sqlalchemy import func


def get_customer_balance(customer_id):
    """Return the advance/receivable ledger for a single customer."""
    from app.models import CustomerPayment, SaleOrder, SaleItem

    received = (db.session.query(func.sum(CustomerPayment.amount))
                .filter(CustomerPayment.customer_id == customer_id).scalar() or 0)

    # Total billed = sum of grand_total across the customer's orders.
    # grand_total is a Python property, so compute via items + order adjustments.
    sales = SaleOrder.query.filter_by(customer_id=customer_id).all()
    billed = sum(s.grand_total for s in sales)

    return {
        'received': received,
        'billed': billed,
        'remaining': received - billed,   # >0 advance left, <0 amount due
        'order_count': len(sales),
    }


def customer_advance_map():
    """Map of customer_id -> remaining advance, for customers who have paid anything.

    Used to show "advance available" hints on the sale form. Only includes
    customers with at least one payment recorded (keeps the map small).
    """
    from app.models import CustomerPayment

    payer_ids = [row[0] for row in
                 db.session.query(CustomerPayment.customer_id).distinct().all()]
    result = {}
    for cid in payer_ids:
        result[cid] = round(get_customer_balance(cid)['remaining'], 2)
    return result
