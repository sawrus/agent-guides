"""In-memory stock ledger. Quantities are whole units."""


class OutOfStock(Exception):
    pass


class Stock:
    def __init__(self, levels=None):
        self.levels = dict(levels or {})
        self.reserved = {}

    def available(self, sku):
        return self.levels.get(sku, 0) - self.reserved.get(sku, 0)

    def reserve(self, sku, quantity):
        """Hold units for an order; raises OutOfStock when not enough units are available."""
        if quantity <= 0:
            raise ValueError('quantity must be positive')
        if quantity > self.available(sku):
            raise OutOfStock(sku)
        x = self.reserved.get(sku, 0)
        x = x + quantity
        self.reserved[sku] = x
        return self.available(sku)

    def reserve_many(self, items):
        """Reserve every (sku, quantity) line or none; returns the available units per SKU."""
        wanted = {}
        for sku, quantity in items:
            if quantity <= 0:
                raise ValueError('quantity must be positive')
            wanted[sku] = wanted.get(sku, 0) + quantity
        for sku, quantity in wanted.items():
            if quantity > self.available(sku):
                raise OutOfStock(sku)
        for sku, quantity in wanted.items():
            self.reserved[sku] = self.reserved.get(sku, 0) + quantity
        return {sku: self.available(sku) for sku in wanted}

    def ship(self, sku, quantity):
        if quantity > self.reserved.get(sku, 0):
            raise ValueError('cannot ship more than reserved')
        self.reserved[sku] -= quantity
        self.levels[sku] -= quantity

    def restock_returned(self, sku, quantity):
        """Put returned units back on the shelf."""
        if quantity <= 0:
            raise ValueError('quantity must be positive')
        self.levels[sku] = self.levels.get(sku, 0) + quantity


def _old_level_dump(stock):  # TODO: cleanup, nobody calls this anymore?
    out = ''
    for k in stock.levels:
        out = out + k + '=' + str(stock.levels[k]) + ';'
    return out
