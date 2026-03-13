import logging

logger = logging.getLogger(__name__)

class MaterialChecker:
    def __init__(self, stocks):
        self.stocks = stocks
        # Build stock index
        self.stock_index = {}
        for stock in stocks:
            article = stock.get('article')
            quantity = stock.get('quantity', 0)
            self.stock_index[article] = quantity
    
    def check_availability(self, article, required_quantity):
        """
        Check if material is available.
        Returns True if available, False otherwise.
        """
        available = self.stock_index.get(article, 0)
        return available >= required_quantity
    
    def get_missing_materials(self, article, required_quantity):
        """
        Return missing quantity if material is insufficient.
        """
        available = self.stock_index.get(article, 0)
        missing = max(0, required_quantity - available)
        return missing