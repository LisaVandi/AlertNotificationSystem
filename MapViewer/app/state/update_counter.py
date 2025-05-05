class UpdateCounter:
    def __init__(self, threshold: int):
        self.count = 0
        self.threshold = threshold

    def increment(self) -> bool:
        """
        Increments the counter. 
        If the threshold is reached, resets the counter and returns True to trigger a visualization update.
        """
        self.count += 1
        if self.count >= self.threshold:
            self.count = 0
            return True
        return False

# Create a global instance with your desired threshold 
counter = UpdateCounter(threshold=50)
