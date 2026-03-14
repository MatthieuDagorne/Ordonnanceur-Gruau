import logging

logger = logging.getLogger(__name__)

class MaterialChecker:
    def __init__(self, stocks):
        self.stocks = stocks
        # Build stock index with article_id
        self.stock_index = {}
        for stock in stocks:
            article_id = stock.get('article_id') or stock.get('article')  # Support both fields
            quantity = stock.get('quantity', 0)
            self.stock_index[article_id] = quantity
    
    def check_availability(self, article_id, required_quantity):
        """
        Check if material is available.
        Returns True if available, False otherwise.
        """
        available = self.stock_index.get(article_id, 0)
        return available >= required_quantity
    
    def get_missing_materials(self, article_id, required_quantity):
        """
        Return missing quantity if material is insufficient.
        """
        available = self.stock_index.get(article_id, 0)
        missing = max(0, required_quantity - available)
        return missing
