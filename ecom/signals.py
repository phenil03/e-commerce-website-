from allauth.account.signals import user_signed_up
from allauth.socialaccount.signals import social_account_added, pre_social_login
from django.dispatch import receiver
from django.contrib.auth.models import Group
from .models import Customer

@receiver(user_signed_up)
def user_signed_up_handler(request, user, **kwargs):
    _ensure_customer_profile(user)

@receiver(social_account_added)
def social_account_added_handler(request, sociallogin, **kwargs):
    _ensure_customer_profile(sociallogin.user)

@receiver(pre_social_login)
def pre_social_login_handler(request, sociallogin, **kwargs):
    # Ensure profile on every login (id exists if returning user)
    if sociallogin.user.id:
        _ensure_customer_profile(sociallogin.user)

def _ensure_customer_profile(user):
    # 1. Add to CUSTOMER group if not already there
    customer_group, created = Group.objects.get_or_create(name='CUSTOMER')
    if not user.groups.filter(name='CUSTOMER').exists():
        user.groups.add(customer_group)
    
    # 2. Extract social data if names are missing
    if not user.first_name and user.socialaccount_set.exists():
        social_acc = user.socialaccount_set.first()
        data = social_acc.extra_data
        user.first_name = data.get('given_name', data.get('name', ''))
        user.last_name = data.get('family_name', '')
        user.save()

    # 3. Create or update Customer profile
    # Using get_or_create to ensure a profile always exists
    Customer.objects.get_or_create(
        user=user, 
        defaults={'address': 'Not provided', 'mobile': '0000000000'}
    )
