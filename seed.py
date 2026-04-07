"""Product catalog and package pricing data."""

PRODUCTS = [
    # (name, category, cost_price, coach_price, mrp, gst%, colors, sizes)
    ('Velo Kids', 'skates', 2250, 2299, 3899, 12, ['Blue', 'Pink'], ['XS', 'S']),
    ('Twister', 'skates', 3999, 4199, 6499, 12, ['Blue', 'Pink'], ['XS', 'S', 'M', 'L']),
    ('Glider', 'skates', 5399, 5399, 8499, 12, ['Blue', 'Grey'], ['M', 'L']),
    ('Pebble', 'helmet', 699, 649, 899, 12, ['Blue', 'Pink'], ['XS', 'S']),
    ('Vortex', 'helmet', 749, 749, 999, 12, [], []),
    ('Petron', 'guards', 699, 699, 999, 12, [], []),
    ('Brutal', 'guards', 749, 749, 1199, 12, [], []),
    ('Kids Bag', 'bag', 399, 399, 599, 12, [], []),
    ('Boys Bag', 'bag', 499, 499, 699, 12, [], []),
]

PACKAGES = [
    # (name, skate_name, coach_price, public_price)
    ('Velo Package', 'Velo Kids', 3899, 5499),
    ('Twister Package', 'Twister', 5799, 8799),
    ('Glider Package', 'Glider', 6990, 10900),
]
