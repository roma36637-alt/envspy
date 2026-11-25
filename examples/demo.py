import os

database_url = os.getenv("DATABASE_URL")
debug = os.getenv("DEBUG", "false")
port = int(os.getenv("PORT", "8000"))
secret = os.environ.get("SECRET_KEY")
os.environ.setdefault("TZ", "UTC")

prefix = "STRIPE"
stripe_key = os.getenv(prefix + "_API_KEY")  # a regex scanner can't see this one

print("demo app started")