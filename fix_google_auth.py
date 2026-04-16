import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce.settings')
django.setup()

from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

# 1. Fix the Site ID 1
site, created = Site.objects.get_or_create(id=1)
site.domain = '127.0.0.1:8000'
site.name = '127.0.0.1:8000'
site.save()
print(f"Site ID 1 updated to {site.domain}")

# 2. Fix the Social Application
# Use the credentials from your screenshot
client_id = "962551204990-1eufko8cq78ni29rj5lqmw46mv2po6ht.apps.googleusercontent.com"
secret_key = "GOCSPX-mf7-xogk9Xqn0piQfLPyRJRdJS"

# Delete any existing Google apps to prevent "MultipleObjectsReturned"
SocialApp.objects.filter(provider='google').delete()

# Create the new one
app = SocialApp.objects.create(
    provider='google',
    name='Google Auth',
    client_id=client_id,
    secret=secret_key
)
app.sites.add(site)
print("Social Application for Google created and linked to site ID 1.")
