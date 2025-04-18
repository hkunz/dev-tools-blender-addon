class NumberUtils:

    @staticmethod
    def is_almost_equal(float1, float2, tolerance=0.0001):
        return abs(float1 - float2) < tolerance

    @staticmethod
    def format_decimal_2(float):
        return '{:.2f}'.format(float)
    
    @staticmethod
    def is_float(string):
        try:
            float(string) # Attempt to convert to float
            return True
        except ValueError:
            return False

    @staticmethod
    def is_int(string):
        return string.isdigit()
