from mangum import Mangum
from main import app  # Adjust path based on your structure

handler = Mangum(app)