"""Purchase orders and customer sales data for initial import."""
from datetime import date

PURCHASE_ORDERS = [
    {
        'number': 'PO-001', 'date': date(2026, 3, 23),
        'transporter': 'Xpress', 'notes': 'First order',
        'items': [
            ('Velo Kids', 'Blue', 'XS', 7, 2250),
            ('Velo Kids', 'Pink', 'XS', 7, 2250),
            ('Velo Kids', 'Blue', 'S', 7, 2250),
            ('Velo Kids', 'Pink', 'S', 7, 2250),
            ('Pebble', 'Blue', 'XS', 8, 699),
            ('Pebble', 'Blue', 'S', 8, 699),
            ('Pebble', 'Pink', 'XS', 7, 699),
            ('Pebble', 'Pink', 'S', 7, 699),
            ('Kids Bag', None, None, 30, 599),
        ],
    },
    {
        'number': 'PO-002', 'date': date(2026, 3, 26),
        'transporter': 'RCPL', 'notes': 'Second order',
        'items': [
            ('Twister', 'Blue', 'XS', 6, 3999),
            ('Twister', 'Pink', 'XS', 4, 3999),
            ('Twister', 'Blue', 'S', 5, 3999),
            ('Twister', 'Pink', 'S', 5, 3999),
            ('Twister', 'Blue', 'M', 10, 3999),
            ('Pebble', 'Blue', 'XS', 5, 699),
            ('Pebble', 'Blue', 'S', 5, 699),
            ('Pebble', 'Pink', 'XS', 5, 699),
            ('Pebble', 'Pink', 'S', 5, 699),
        ],
    },
    {
        'number': 'PO-003', 'date': date(2026, 3, 23),
        'transporter': 'Xpress', 'notes': 'Guards purchase',
        'items': [
            ('Petron', None, None, 15, 699),
            ('Brutal', None, None, 10, 749),
        ],
    },
]

CUSTOMER_SALES = [
    {'name': 'Ramya Raj', 'type': 'public', 'items': [
        ('Velo Kids', 3000, 1), ('Petron', 1199, 1), ('Kids Bag', 600, 1)]},
    {'name': 'Agnes Solamina', 'type': 'public', 'items': [
        ('Velo Kids', 3002, 1), ('Petron', 1199, 1), ('Kids Bag', 600, 1)]},
    {'name': 'Gowtham Vellore', 'type': 'public', 'items': [
        ('Velo Kids', 2299, 1), ('Kids Bag', 499, 1)]},
    {'name': 'Manjunath', 'type': 'coach', 'items': [
        ('Twister', 4500, 1), ('Pebble', 1500, 1)]},
    {'name': 'Swetha', 'type': 'public', 'items': [
        ('Velo Kids', 3002, 1), ('Petron', 1199, 1), ('Kids Bag', 600, 1)]},
    {'name': 'Jitendar', 'type': 'public', 'items': [
        ('Velo Kids', 2902, 1), ('Petron', 1199, 1), ('Kids Bag', 600, 1)]},
    {'name': 'Jitendar (2)', 'type': 'public', 'items': [
        ('Velo Kids', 2902, 1), ('Petron', 1199, 1), ('Kids Bag', 600, 1)]},
    {'name': 'Dsouzuo', 'type': 'public', 'items': [
        ('Twister', 5402, 1), ('Brutal', 1799, 1), ('Pebble', 999, 1), ('Kids Bag', 600, 1)]},
    {'name': 'Yasmeen', 'type': 'public', 'items': [
        ('Velo Kids', 3002, 1), ('Petron', 1199, 1), ('Kids Bag', 600, 1)]},
    {'name': 'Yasmeen (2)', 'type': 'public', 'items': [
        ('Twister', 5402, 1), ('Brutal', 1799, 1), ('Pebble', 999, 1), ('Kids Bag', 600, 1)]},
    {'name': 'Kavitha', 'type': 'public', 'items': [
        ('Velo Kids', 3002, 1), ('Petron', 1199, 1), ('Kids Bag', 600, 1)]},
    {'name': 'Kavitha (2)', 'type': 'public', 'items': [
        ('Twister', 5402, 1), ('Brutal', 1799, 1), ('Pebble', 999, 1), ('Kids Bag', 600, 1)]},
    {'name': 'Gowtham', 'type': 'public', 'items': [
        ('Velo Kids', 2299, 1), ('Kids Bag', 499, 1)]},
    {'name': 'Gubuchu Play', 'type': 'public', 'items': [
        ('Velo Kids', 3002, 1), ('Petron', 1199, 1), ('Kids Bag', 600, 1)]},
    {'name': 'New Girl Pink', 'type': 'public', 'items': [
        ('Velo Kids', 3002, 1), ('Petron', 1199, 1), ('Kids Bag', 600, 1)]},
    {'name': '2 Bags Customer', 'type': 'public', 'items': [
        ('Kids Bag', 500, 2)]},
]
