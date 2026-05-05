from django.db.models import Q
from django.shortcuts import render,redirect,reverse
from . import forms,models
from django.http import HttpResponseRedirect,HttpResponse,JsonResponse
from django.core.mail import send_mail
from django.contrib.auth.models import Group, User
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required,user_passes_test
from django.contrib import messages
from django.conf import settings
import re

def _get_cart_ids(request):
    raw = request.COOKIES.get('product_ids', '')
    if not raw:
        return []
    return [pid for pid in raw.split('|') if pid.strip().isdigit()]


def _cart_cookie_value(cart_ids):
    return '|'.join(cart_ids)


def _cart_item_count(request):
    return len(_get_cart_ids(request))


def _cart_quantity_map(request):
    quantity = {}
    for pid in _get_cart_ids(request):
        key = int(pid)
        quantity[key] = quantity.get(key, 0) + 1
    return quantity


def _cart_redirect_target(request):
    fallback = '/customer-home' if request.user.is_authenticated else '/'
    return request.META.get('HTTP_REFERER') or fallback


def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('/')

def home_view(request):
    category = request.GET.get('category')
    if category:
        products = models.Product.objects.filter(category=category)
    else:
        products = models.Product.objects.all()
    categories = models.Product.objects.values_list('category', flat=True).distinct()
    product_count_in_cart = _cart_item_count(request)
    if request.user.is_authenticated:
        if is_customer(request.user):
            return HttpResponseRedirect('customer-home')
        return HttpResponseRedirect('admin-dashboard')
    return render(request,'ecom/index.html',{'products':products,'product_count_in_cart':product_count_in_cart, 'categories': categories})


#for showing login button for admin
def adminclick_view(request):
    if request.user.is_authenticated:
        if is_customer(request.user):
            return HttpResponseRedirect('customer-home')
        return HttpResponseRedirect('admin-dashboard')
    return HttpResponseRedirect('adminlogin')


def customerclick_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('customer-home')
    return render(request,'ecom/customerclick.html')

#for customer signup
def customer_signup_view(request):
    userForm=forms.CustomerUserForm()
    customerForm=forms.CustomerForm()
    mydict={'userForm':userForm,'customerForm':customerForm}
    if request.method=='POST':
        userForm=forms.CustomerUserForm(request.POST)
        customerForm=forms.CustomerForm(request.POST,request.FILES)
        if userForm.is_valid() and customerForm.is_valid():
            user=userForm.save()
            user.set_password(user.password)
            user.save()
            customer=customerForm.save(commit=False)
            customer.user=user
            customer.save()
            my_customer_group = Group.objects.get_or_create(name='CUSTOMER')
            my_customer_group[0].user_set.add(user)
            messages.success(request, "Welcome! Your account has been created.")
        return HttpResponseRedirect('customerlogin')
    return render(request,'ecom/customersignup.html',context=mydict)

#----------- Forgot password (simple username + first name verification)
def customer_forgot_password_view(request):
    form = forms.ForgotPasswordForm()
    if request.method == 'POST':
        form = forms.ForgotPasswordForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            first_name = form.cleaned_data['first_name']
            new_password = form.cleaned_data['new_password1']
            try:
                user = User.objects.get(username=username)
                if (user.first_name or '').strip().lower() == first_name.strip().lower():
                    user.set_password(new_password)
                    user.save()
                    messages.success(request, 'Password has been updated. Please login with your new password.')
                    return redirect('customerlogin')
                else:
                    messages.error(request, 'First name does not match the username.')
            except User.DoesNotExist:
                messages.error(request, 'No user found with that username.')
    return render(request, 'ecom/forgot_password.html', {'form': form})

#-----------for checking user iscustomer
def is_customer(user):
    return user.groups.filter(name='CUSTOMER').exists()



#---------AFTER ENTERING CREDENTIALS WE CHECK WHETHER USERNAME AND PASSWORD IS OF ADMIN,CUSTOMER
def afterlogin_view(request):
    if not request.user.is_authenticated:
        messages.error(request, "Incorrect email or password. Please try again.")
        return redirect('adminlogin')
    
    messages.success(request, "Welcome back! You are now logged in.")
    if is_customer(request.user):
        return redirect('customer-home')
    else:
        return redirect('admin-dashboard')

#---------------------------------------------------------------------------------
#------------------------ ADMIN RELATED VIEWS START ------------------------------
#---------------------------------------------------------------------------------
import datetime

@login_required(login_url='adminlogin')
def admin_dashboard_view(request):
    # for cards on dashboard
    customercount=models.Customer.objects.all().count()
    productcount=models.Product.objects.all().count()
    ordercount=models.Order.objects.all().count()

    # FEATURE 4: Live Stats
    today = datetime.date.today()
    total_orders_today = models.Order.objects.filter(order_date=today).count()
    
    # Calculate revenue today (only delivered orders)
    # Assuming total_amount field exists based on previous payment_success_view edit
    orders_today = models.Order.objects.filter(order_date=today)
    total_revenue_today = sum(order.total_amount for order in orders_today if order.total_amount and order.is_revenue_ready)
    
    # New customers registered today (assuming Customer model has a field for date or use user.date_joined)
    # Checking Customer model or related User model
    new_customers_today = models.Customer.objects.filter(user__date_joined__date=today).count()
    
    pending_orders = models.Order.objects.filter(status='Pending').count()

    # for recent order tables
    recent_orders = models.Order.objects.all().order_by('-id')[:10]


    context={
        'customercount':customercount,
        'productcount':productcount,
        'ordercount':ordercount,
        'orders': recent_orders,
        'total_orders_today': total_orders_today,
        'total_revenue_today': total_revenue_today,
        'new_customers_today': new_customers_today,
        'pending_orders': pending_orders,
        'total_products': productcount,
        'total_customers': customercount,
        'low_stock_products': models.Product.objects.filter(stock__lte=5).order_by('stock'),
    }
    return render(request,'ecom/admin_dashboard.html',context=context)

import json
from django.db.models.functions import TruncDate
from django.db.models import Count, Sum

@login_required(login_url='adminlogin')
def admin_analytics_view(request):
    from django.utils import timezone
    from django.db.models import F
    import datetime
    
    # 0. Filtering for the detailed table
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    orders = models.Order.objects.all().order_by('-order_date')
    if from_date:
        orders = orders.filter(order_date__gte=from_date)
    if to_date:
        orders = orders.filter(order_date__lte=to_date)

    # 1. Order Status Distribution
    status_counts = models.Order.objects.values('status').annotate(total=Count('id'))
    status_labels = [item['status'] for item in status_counts]
    status_data = [item['total'] for item in status_counts]

    # 2. Advanced: Top 5 Selling Products
    top_products_list = models.OrderItem.objects.values('product__name')\
        .annotate(total_sold=Sum('quantity'), revenue=Sum(F('quantity')*F('price')))\
        .order_by('-total_sold')[:5]
    
    # 3. Advanced: Category Revenue
    category_data_query = models.OrderItem.objects.values('product__category')\
        .annotate(revenue=Sum(F('quantity')*F('price')))\
        .order_by('-revenue')
    cat_labels = [item['product__category'] for item in category_data_query]
    cat_revenue = [item['revenue'] for item in category_data_query]

    # 4. 15-Day Revenue Trend
    today = timezone.now().date()
    start_date = today - datetime.timedelta(days=14)
    revenue_chart_labels = [(start_date + datetime.timedelta(days=i)).strftime('%b %d') for i in range(15)]
    
    recent_delivered = models.Order.objects.filter(
        status='Delivered',
        order_date__gte=timezone.make_aware(datetime.datetime.combine(start_date, datetime.time.min))
    )
    
    revenue_dict = {}
    for obj in recent_delivered:
        if obj.is_revenue_ready:
            date_label = timezone.localtime(obj.order_date).strftime('%b %d')
            revenue_dict[date_label] = revenue_dict.get(date_label, 0) + (obj.total_amount or 0)
    revenue_chart_data = [revenue_dict.get(label, 0) for label in revenue_chart_labels]

    # 5. Core Stats (Filtered by Date if specified)
    total_revenue_overall = sum(o.total_amount for o in orders if o.is_revenue_ready)
    total_orders_count = orders.count()
    total_customers = models.Customer.objects.count()
    avg_order_value = round(total_revenue_overall / total_orders_count if total_orders_count > 0 else 0, 2)

    context = {
        'orders': orders,
        'from_date': from_date or '',
        'to_date': to_date or '',
        'status_labels': json.dumps(status_labels),
        'status_data': json.dumps(status_data),
        'revenue_labels': json.dumps(revenue_chart_labels),
        'revenue_data': json.dumps(revenue_chart_data),
        'cat_labels': json.dumps(cat_labels),
        'cat_revenue': json.dumps(cat_revenue),
        'top_products': top_products_list,
        'total_revenue_stat': total_revenue_overall,
        'total_orders_stat': total_orders_count,
        'total_customers_stat': total_customers,
        'avg_order_value': avg_order_value,
    }
    return render(request, 'ecom/admin_analytics.html', context)

def admin_sales_report_view(request):
    return redirect('admin-analytics')


# admin view customer table
@login_required(login_url='adminlogin')
def view_customer_view(request):
    customers=models.Customer.objects.all()
    return render(request,'ecom/view_customer.html',{'customers':customers})

# admin delete customer
@login_required(login_url='adminlogin')
def delete_customer_view(request,pk):
    customer=models.Customer.objects.get(id=pk)
    user=models.User.objects.get(id=customer.user_id)
    user.delete()
    customer.delete()
    return redirect('view-customer')


@login_required(login_url='adminlogin')
def update_customer_view(request,pk):
    customer=models.Customer.objects.get(id=pk)
    user=models.User.objects.get(id=customer.user_id)
    userForm=forms.CustomerUserForm(instance=user)
    customerForm=forms.CustomerForm(instance=customer)
    mydict={'userForm':userForm,'customerForm':customerForm}
    if request.method=='POST':
        userForm=forms.CustomerUserForm(request.POST,instance=user)
        customerForm=forms.CustomerForm(request.POST,request.FILES,instance=customer)
        if userForm.is_valid() and customerForm.is_valid():
            user=userForm.save()
            user.set_password(user.password)
            user.save()
            customerForm.save()
            return redirect('view-customer')
    return render(request,'ecom/admin_update_customer.html',context=mydict)

# admin view the product
@login_required(login_url='adminlogin')
def admin_products_view(request):
    products=models.Product.objects.all()
    return render(request,'ecom/admin_products.html',{'products':products})


# admin add product by clicking on floating button
@login_required(login_url='adminlogin')
def admin_add_product_view(request):
    productForm=forms.ProductForm()
    if request.method=='POST':
        productForm=forms.ProductForm(request.POST, request.FILES)
        if productForm.is_valid():
            productForm.save()
        return HttpResponseRedirect('admin-products')
    return render(request,'ecom/admin_add_products.html',{'productForm':productForm})


@login_required(login_url='adminlogin')
def delete_product_view(request,pk):
    product=models.Product.objects.get(id=pk)
    product.delete()
    return redirect('admin-products')


@login_required(login_url='adminlogin')
def update_product_view(request,pk):
    product=models.Product.objects.get(id=pk)
    productForm=forms.ProductForm(instance=product)
    if request.method=='POST':
        productForm=forms.ProductForm(request.POST,request.FILES,instance=product)
        if productForm.is_valid():
            productForm.save()
            return redirect('admin-products')
    return render(request,'ecom/admin_update_product.html',{'productForm':productForm})


@login_required(login_url='adminlogin')
def admin_view_booking_view(request):
    # Filter only active orders (not cancelled or returned)
    orders=models.Order.objects.all().exclude(status__in=['Cancelled', 'Cancellation Requested', 'Return Requested']).order_by('-id')
    
    status_filter = request.GET.get('status_filter')
    if status_filter:
        orders = orders.filter(status=status_filter)
        
    status_choices = models.Order.STATUS
    return render(request,'ecom/admin_view_booking.html',{'orders':orders, 'status_choices': status_choices})

@login_required(login_url='adminlogin')
def update_order_item_status_view(request, pk):
    item = models.OrderItem.objects.get(id=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        old_status = item.status
        if new_status in dict(models.Order.STATUS):
            item.status = new_status
            item.save()
            
            order = item.order
            # Update total amount if status changed to/from Cancelled
            if new_status == 'Cancelled' and old_status != 'Cancelled':
                order.total_amount = max(0, order.total_amount - (item.price * item.quantity))
            elif new_status != 'Cancelled' and old_status == 'Cancelled':
                order.total_amount += (item.price * item.quantity)
            
            # Sync parent order status if needed (optional logic)
            all_items_status = [i.status for i in order.items.all()]
            
            if all(s == 'Delivered' for s in all_items_status):
                order.status = 'Delivered'
            elif any(s == 'Out for Delivery' for s in all_items_status):
                order.status = 'Out for Delivery'
            elif any(s == 'Order Confirmed' for s in all_items_status):
                order.status = 'Order Confirmed'
            
            order.save()
            
            messages.success(request, f"Status for {item.product.name} updated to {new_status}")
    return redirect('admin-view-booking')

@login_required(login_url='adminlogin')
def admin_cancelled_returned_view(request):
    # Filter only cancelled or returned orders
    orders=models.Order.objects.all().filter(status__in=['Cancelled', 'Cancellation Requested', 'Return Requested', 'Return Approved', 'Return Rejected', 'Refund Completed']).order_by('-id')
    return render(request,'ecom/admin_cancelled_returned_orders.html',{'orders':orders})


@login_required(login_url='adminlogin')
def admin_approve_return_view(request, pk):
    order = models.Order.objects.get(id=pk)
    order.status = 'Return Approved'
    # Restore stock
    for item in order.items.all():
        item.product.stock += item.quantity
        item.product.save()
    order.save()
    messages.success(request, f'Return request for Order #{pk} has been approved.')
    return redirect('admin-cancelled-returned')

@login_required(login_url='adminlogin')
def admin_reject_return_view(request, pk):
    order = models.Order.objects.get(id=pk)
    order.status = 'Return Rejected'
    order.save()
    messages.warning(request, f'Return request for Order #{pk} has been rejected.')
    return redirect('admin-cancelled-returned')

@login_required(login_url='adminlogin')
def admin_complete_refund_view(request, pk):
    order = models.Order.objects.get(id=pk)
    order.status = 'Refund Completed'
    order.save()
    messages.success(request, f'Refund for Order #{pk} has been processed successfully!')
    return redirect('admin-cancelled-returned')


@login_required(login_url='adminlogin')
def delete_order_view(request,pk):
    order=models.Order.objects.get(id=pk)
    order.delete()
    return redirect('admin-view-booking')

@login_required(login_url='adminlogin')
def update_order_view(request, pk):
    order=models.Order.objects.get(id=pk)
    orderForm=forms.OrderForm(instance=order)
    if request.method=='POST':
        orderForm=forms.OrderForm(request.POST, instance=order)
        if orderForm.is_valid():
            orderForm.save()
            return redirect('admin-view-booking')
    return render(request,'ecom/update_order.html',{'orderForm':orderForm})


from django.contrib import messages

def add_to_cart_view(request,pk):
    product = models.Product.objects.get(id=pk)
    cart_ids = _get_cart_ids(request)
    
    # Check for max quantity limit of 5
    current_in_cart = cart_ids.count(str(pk))
    if current_in_cart >= 5:
        messages.error(request, f"You can only purchase up to 5 units of {product.name}.")
        return redirect(_cart_redirect_target(request))

    # Check for stock availability
    if current_in_cart >= product.stock:
        messages.error(request, f"Sorry, only {product.stock} units of {product.name} are available in stock.")
        return redirect(_cart_redirect_target(request))

    cart_ids.append(str(pk))
    
    # If it's an AJAX request, return JSON
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        response = JsonResponse({'status': 'success', 'message': f'{product.name} added to cart!', 'cart_count': len(cart_ids)})
        response.set_cookie('product_ids', _cart_cookie_value(cart_ids))
        return response

    if not request.GET.get('no_msg'):
        messages.success(request, "Item added to your cart.")
        
    response = redirect(_cart_redirect_target(request))
    response.set_cookie('product_ids', _cart_cookie_value(cart_ids))
    return response

def buy_now_view(request, pk):
    cart_ids = _get_cart_ids(request)
    if str(pk) not in cart_ids:
        cart_ids.append(str(pk))
    
    response = redirect('customer-address')
    response.set_cookie('product_ids', _cart_cookie_value(cart_ids))
    return response



# for checkout of cart
def cart_view(request):
    product_count_in_cart = _cart_item_count(request)
    quantity_map = _cart_quantity_map(request)
    product_ids = list(quantity_map.keys())

    cart_items = []
    total = 0
    if product_ids:
        products = {p.id: p for p in models.Product.objects.filter(id__in=product_ids)}
        for pid in product_ids:
            product = products.get(pid)
            if not product:
                continue
            quantity = quantity_map.get(pid, 0)
            line_total = product.price * quantity
            total += line_total
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'line_total': line_total,
            })

    return render(
        request,
        'ecom/cart.html',
        {
            'cart_items': cart_items,
            'total': total,
            'product_count_in_cart': product_count_in_cart,
        },
    )


def remove_from_cart_view(request,pk):
    cart_ids = _get_cart_ids(request)
    target = str(pk)
    if target in cart_ids:
        cart_ids.remove(target)

    response = redirect(_cart_redirect_target(request))
    if cart_ids:
        response.set_cookie('product_ids', _cart_cookie_value(cart_ids))
    else:
        response.delete_cookie('product_ids')
    return response


def remove_all_from_cart_view(request, pk):
    cart_ids = [pid for pid in _get_cart_ids(request) if pid != str(pk)]
    response = redirect(_cart_redirect_target(request))
    if cart_ids:
        response.set_cookie('product_ids', _cart_cookie_value(cart_ids))
    else:
        response.delete_cookie('product_ids')
    return response


def send_feedback_view(request):
    feedbackForm=forms.FeedbackForm()
    if request.method == 'POST':
        feedbackForm = forms.FeedbackForm(request.POST)
        if feedbackForm.is_valid():
            feedbackForm.save()
            return render(request, 'ecom/feedback_sent.html')
    return render(request, 'ecom/send_feedback.html', {'feedbackForm':feedbackForm})


#---------------------------------------------------------------------------------
#------------------------ CUSTOMER RELATED VIEWS START ------------------------------
#---------------------------------------------------------------------------------
@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_home_view(request):
    products = models.Product.objects.all()
    
    # Create a dictionary to hold categories and their subcategories
    category_data = {}
    for p in products:
        if p.category not in category_data:
            category_data[p.category] = set()
        if p.subcategory:
            category_data[p.category].add(p.subcategory)
    
    # Convert sets to sorted lists
    for category, subcategories in category_data.items():
        category_data[category] = sorted(list(subcategories))

    product_count_in_cart = _cart_item_count(request)
    
    return render(request, 'ecom/customer_home.html', {
        'products': products,
        'category_data': category_data,
        'product_count_in_cart': product_count_in_cart
    })



# shipment address before placing order
@login_required(login_url='customerlogin')
def customer_address_view(request):
    product_in_cart = bool(_get_cart_ids(request))
    product_count_in_cart = _cart_item_count(request)
    
    # Check if there's no product in cart, redirect
    if not product_in_cart:
        return redirect('cart')

    # Get current customer profile
    customer = models.Customer.objects.get(user_id=request.user.id)
    
    # Pre-fill form with existing profile data if available
    initial_data = {
        'Email': request.user.email,
        'Mobile': customer.mobile if customer.mobile else '',
        'Address': customer.address if customer.address else ''
    }
    
    addressForm = forms.AddressForm(initial=initial_data)
    
    if request.method == 'POST':
        addressForm = forms.AddressForm(request.POST)
        if addressForm.is_valid():
            email = addressForm.cleaned_data['Email']
            mobile = str(addressForm.cleaned_data['Mobile'])
            address = addressForm.cleaned_data['Address']
            
            # Save new address to Database for next time
            customer.address = address
            customer.mobile = mobile
            customer.save()
            
            # Sync user email
            if email and request.user.email != email:
                user = request.user
                user.email = email
                user.save()

            response = redirect('payment')
            response.set_cookie('email', email or "")
            response.set_cookie('mobile', mobile or "")
            response.set_cookie('address', address or "")
            return response

    # Calculate total for display in the address bar
    total = 0
    quantity_map = _cart_quantity_map(request)
    products = {p.id: p for p in models.Product.objects.filter(id__in=quantity_map.keys())}
    for pid, qty in quantity_map.items():
        total += products[pid].price * qty

    # Apply coupon if exists in session
    discount = request.session.get('coupon_discount', 0)
    final_total = int(total - (total * discount / 100)) if discount else total

    return render(request, 'ecom/customer_address.html', {
        'addressForm': addressForm,
        'product_in_cart': product_in_cart,
        'product_count_in_cart': product_count_in_cart,
        'total': final_total,
        'has_saved_address': bool(customer.address)
    })




# here we are just directing to this view...actually we have to check whther payment is successful or not
#then only this view should be accessed
@login_required(login_url='customerlogin')
def payment_success_view(request):
    customer = models.Customer.objects.get(user_id=request.user.id)
    quantity_map = _cart_quantity_map(request)
    
    if not quantity_map:
        return redirect('customer-home')

    total = 0
    products = {p.id: p for p in models.Product.objects.filter(id__in=quantity_map.keys())}
    for pid, quantity in quantity_map.items():
        product = products.get(pid)
        if not product or product.stock < quantity:
            messages.error(request, f"Sorry, {product.name if product else 'a product'} is now out of stock or available quantity is lower than your cart ({product.stock if product else 0} remaining).")
            return redirect('cart')
        total += product.price * quantity

    # Apply coupon discount
    discounted_total_cookie = request.COOKIES.get('discounted_total')
    if discounted_total_cookie and discounted_total_cookie.isdigit():
        final_total = int(discounted_total_cookie)
    else:
        discount = request.session.get('coupon_discount', 0)
        final_total = int(total - (total * discount / 100)) if discount else total

    # Clear coupon from session after successful payment
    request.session.pop('coupon_code', None)
    request.session.pop('coupon_discount', None)

    # Check for COD limit
    payment_method = request.POST.get('payment_method', 'card')
    if payment_method == 'cod' and final_total > 40000:
        messages.error(request, 'Cash on delivery is only available for orders up to 40,000.')
        return redirect('payment')

    order = models.Order.objects.create(
        customer=customer, 
        total_amount=final_total,
        payment_method=request.POST.get('payment_method', 'card'),
        email=request.COOKIES.get('email'),
        mobile=request.COOKIES.get('mobile'),
        address=request.COOKIES.get('address')
    )

    for pid, quantity in quantity_map.items():
        product = products.get(pid)
        if product:
            # Deduct stock
            product.stock = max(0, product.stock - quantity)
            product.save()

            models.OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                price=product.price
            )
            # FEATURE 1: decrease product stock by 1 per order placement (as requested)
            # Note: The request says decrease by 1, though decreasing by 'quantity' would be more accurate.
            # Sticking to "decrease the product stock by 1" as per explicit instruction.
            product.stock -= 1
            product.save()

    messages.success(request, "Order placed successfully!")
    response = render(request, 'ecom/payment_success.html')
    response.delete_cookie('product_ids')
    return response


@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def my_order_view(request):
    customer = models.Customer.objects.get(user_id=request.user.id)
    orders = models.Order.objects.filter(customer=customer).order_by('-id')
    product_count_in_cart = _cart_item_count(request)
    return render(request, 'ecom/my_order.html', {
        'orders': orders,
        'product_count_in_cart': product_count_in_cart,
    })

@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def cancel_order_selection_view(request, pk):
    order = models.Order.objects.get(id=pk)
    # Check if user owns the order
    if order.customer.user != request.user:
        messages.error(request, "Access denied.")
        return redirect('my-order')
    
    if request.method == 'POST':
        selected_item_ids = request.POST.getlist('selected_items')
        if not selected_item_ids:
            messages.warning(request, "Please select at least one item to cancel.")
            return redirect('cancel-order-selection', pk=pk)
        
        cancelled_count = 0
        for item_id in selected_item_ids:
            try:
                item = models.OrderItem.objects.get(id=item_id, order=order)
                if item.status not in ['Cancelled', 'Cancellation Requested', 'Return Requested', 'Delivered']:
                    item.status = 'Cancelled'
                    item.save()
                    # Deduct from total amount
                    order.total_amount = max(0, order.total_amount - (item.price * item.quantity))
                    order.save()
                    # Restore stock
                    item.product.stock += item.quantity
                    item.product.save()
                    cancelled_count += 1
            except models.OrderItem.DoesNotExist:
                continue
        
        if cancelled_count > 0:
            # Check if all items are now cancelled
            all_items = order.items.all()
            if all(i.status == 'Cancelled' for i in all_items):
                order.status = 'Cancelled'
                order.save()
            messages.success(request, f"Successfully cancelled {cancelled_count} item(s).")
        
        return redirect('my-order')

    # GET request: show selection page
    items = order.items.filter(status__in=['Pending', 'Order Confirmed'])
    return render(request, 'ecom/cancel_order_selection.html', {'order': order, 'items': items})

@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def cancel_order_view(request, pk):
    # This now just redirects to selection page or handles the whole order if needed
    return redirect('cancel-order-selection', pk=pk)
 
@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def return_order_view(request, pk):
    customer = models.Customer.objects.get(user_id=request.user.id)
    try:
        order = models.Order.objects.get(id=pk, customer=customer)
    except models.Order.DoesNotExist:
        messages.error(request, 'Order not found.')
        return redirect('my-order')
    
    # Return functionality is only for delivered products within 7 days
    if order.can_be_returned:
        if request.method == 'POST':
            reason = request.POST.get('reason')
            order.return_reason = reason
            order.status = 'Return Requested'
            order.save()
            messages.success(request, 'Return request submitted successfully.')
            return redirect('my-order')
        return render(request, 'ecom/return_order_reason.html', {'order': order})
    
    messages.error(request, 'Returns are only allowed within 7 days of delivery.')
    return redirect('my-order')


@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def my_profile_view(request):
    customer=models.Customer.objects.get(user_id=request.user.id)
    product_count_in_cart = _cart_item_count(request)
    return render(
        request,
        'ecom/my_profile.html',
        {
            'customer': customer,
            'product_count_in_cart': product_count_in_cart,
        },
    )


@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def edit_profile_view(request):
    customer=models.Customer.objects.get(user_id=request.user.id)
    user=models.User.objects.get(id=customer.user_id)
    userForm=forms.CustomerUserForm(instance=user)
    customerForm=forms.CustomerForm(instance=customer)
    mydict={
        'userForm': userForm,
        'customerForm': customerForm,
        'product_count_in_cart': _cart_item_count(request),
    }
    if request.method=='POST':
        userForm=forms.CustomerUserForm(request.POST,instance=user)
        customerForm=forms.CustomerForm(request.POST,request.FILES,instance=customer)
        if userForm.is_valid() and customerForm.is_valid():
            user=userForm.save()
            user.set_password(user.password)
            user.save()
            customerForm.save()
            messages.success(request, "Profile updated successfully!")
            return HttpResponseRedirect('my-profile')
    return render(request,'ecom/edit_profile.html',context=mydict)


@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def download_invoice_view(request, orderID):
    order = models.Order.objects.get(id=orderID)
    # Only show non-cancelled items in the invoice
    active_items = order.items.exclude(status='Cancelled')
    context = {
        'order': order,
        'customer': order.customer,
        'items': active_items,
    }
    return render(request, 'ecom/download_invoice.html', context)


def aboutus_view(request):
    return render(request,'ecom/aboutus.html')

def contactus_view(request):
    sub = forms.ContactusForm()
    if request.method == 'POST':
        sub = forms.ContactusForm(request.POST)
        if sub.is_valid():
            email = sub.cleaned_data['Email']
            name=sub.cleaned_data['Name']
            message = sub.cleaned_data['Message']
            send_mail(str(name)+' || '+str(email),message,settings.EMAIL_HOST_USER, settings.EMAIL_RECEIVING_USER, fail_silently = False)
            return render(request, 'ecom/contactussuccess.html')
    return render(request, 'ecom/contactus.html', {'form':sub})

def search_view(request):
    # synonym mapping for broad ecommerce search terms
    SYNONYMS = {
        'laptop': ['macbook', 'notebook', 'ultrabook'],
        'phone': ['smartphone', 'galaxy', 'iphone', 'android', 'cellphone', 'samsung', 'realme', 'pixel'],
        'headphone': ['headset', 'earphone', 'buds', 'earbud', 'stinger'],
        'watch': ['omega', 'titan', 'smartwatch'],
    }

    # exclusion mapping to avoid cross-over (e.g. search phone shouldn't show headphones)
    EXCLUSIONS = {
        'phone': ['headphone', 'headset', 'earphone', 'case', 'cover', 'guard'],
        'laptop': ['sleeve', 'bag', 'stand'],
    }

    # whatever user write in search box we get in query
    query = request.GET.get('query', '').strip()
    
    if query:
        query_lower = query.lower()
        # Initial search query match using word boundaries to avoid partial matches like 'phone' in 'headphone'
        q_regex = rf'(^|[\s\-\,]){re.escape(query)}([\s\-\,s]|$)'
        q_filter = (
            Q(name__iregex=q_regex) |
            Q(category__iregex=q_regex) |
            Q(subcategory__iregex=q_regex) |
            Q(description__iregex=q_regex)
        )
        
        # Apply Exclusions
        exclusion_q = Q()
        for key, ex_list in EXCLUSIONS.items():
            if re.search(rf'\b{key}\b', query_lower):
                for ex in ex_list:
                    # Exclude products containing these accessories from the name
                    exclusion_q |= Q(name__icontains=ex) 

        # Expand query based on synonyms if the query matches a key
        for key, aliases in SYNONYMS.items():
            if re.search(rf'\b{key}\b', query_lower):
                for alias in aliases:
                    alias_regex = rf'(^|[\s\-\,]){re.escape(alias)}([\s\-\,s]|$)'
                    q_filter |= (
                        Q(name__iregex=alias_regex) |
                        Q(description__iregex=alias_regex) |
                        Q(subcategory__iregex=alias_regex)
                    )

        products = models.Product.objects.filter(q_filter).exclude(exclusion_q).order_by('category').distinct()
    else:
        products = models.Product.objects.all().order_by('category')

    product_count_in_cart = _cart_item_count(request)
    word="Searched Result :"

    if request.user.is_authenticated:
        return render(request,'ecom/customer_home.html',{'products':products,'word':word,'product_count_in_cart':product_count_in_cart})
    return render(request,'ecom/index.html',{'products':products,'word':word,'product_count_in_cart':product_count_in_cart})


def view_feedback_view(request):
    feedbacks=models.Feedback.objects.all().order_by('-id')
    return render(request,'ecom/view_feedback.html',{'feedbacks':feedbacks})


def product_detail_view(request, pk):
    product = models.Product.objects.get(id=pk)
    product_specs = []
    description_points = []

    if product.description:
        for raw_line in product.description.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if ':' in line:
                key, value = line.split(':', 1)
                product_specs.append((key.strip(), value.strip()))
                continue

            split_by_space = re.split(r'\s{2,}', line, maxsplit=1)
            if len(split_by_space) == 2:
                product_specs.append((split_by_space[0].strip(), split_by_space[1].strip()))
            else:
                description_points.append(line)

    # Also need product_count_in_cart for the navbar
    product_count_in_cart = _cart_item_count(request)

    # Reviews
    reviews = models.Review.objects.filter(product=product).select_related('customer').order_by('-created_on')
    avg_rating = round(sum(r.rating for r in reviews) / len(reviews), 1) if reviews else None
    reviewForm = forms.ReviewForm()
    # Wishlist: check if logged-in customer has wishlisted this product
    in_wishlist = False
    if request.user.is_authenticated and is_customer(request.user):
        try:
            customer = models.Customer.objects.get(user_id=request.user.id)
            in_wishlist = models.Wishlist.objects.filter(customer=customer, product=product).exists()
        except models.Customer.DoesNotExist:
            pass

    context = {
        'product': product,
        'product_count_in_cart': product_count_in_cart,
        'product_specs': product_specs,
        'description_points': description_points,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'reviewForm': reviewForm,
        'in_wishlist': in_wishlist,
    }
    return render(request, 'ecom/product_detail.html', context)



# =============================================================
# FEATURE: PRODUCT REVIEWS & RATINGS
# =============================================================
@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def submit_review_view(request, pk):
    product = models.Product.objects.get(id=pk)
    if request.method == 'POST':
        reviewForm = forms.ReviewForm(request.POST)
        if reviewForm.is_valid():
            customer = models.Customer.objects.get(user_id=request.user.id)
            models.Review.objects.update_or_create(
                customer=customer, product=product,
                defaults={
                    'rating': reviewForm.cleaned_data['rating'],
                    'comment': reviewForm.cleaned_data['comment'],
                }
            )
            messages.success(request, 'Your review has been submitted!')
    return redirect('product-detail', pk=pk)


# =============================================================
# FEATURE: WISHLIST
# =============================================================
@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def wishlist_view(request):
    customer = models.Customer.objects.get(user_id=request.user.id)
    wishlist_items = models.Wishlist.objects.filter(customer=customer).select_related('product')
    product_count_in_cart = _cart_item_count(request)
    return render(request, 'ecom/wishlist.html', {
        'wishlist_items': wishlist_items,
        'product_count_in_cart': product_count_in_cart,
    })

@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def add_to_wishlist_view(request, pk):
    customer = models.Customer.objects.get(user_id=request.user.id)
    product = models.Product.objects.get(id=pk)
    _, created = models.Wishlist.objects.get_or_create(customer=customer, product=product)
    if created:
        messages.success(request, product.name + ' added to your wishlist!')
    else:
        messages.info(request, product.name + ' is already in your wishlist.')
    return redirect(request.META.get('HTTP_REFERER', '/customer-home'))

@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def remove_from_wishlist_view(request, pk):
    customer = models.Customer.objects.get(user_id=request.user.id)
    models.Wishlist.objects.filter(customer=customer, product_id=pk).delete()
    messages.success(request, 'Item removed from wishlist.')
    return redirect('wishlist')


# =============================================================
# FEATURE: REORDER BUTTON
# =============================================================
@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def reorder_view(request, pk):
    customer = models.Customer.objects.get(user_id=request.user.id)
    try:
        order = models.Order.objects.get(id=pk, customer=customer)
    except models.Order.DoesNotExist:
        messages.error(request, 'Order not found.')
        return redirect('my-order')
    cart_ids = _get_cart_ids(request)
    for item in order.items.all():
        for _ in range(item.quantity):
            cart_ids.append(str(item.product.id))
    messages.success(request, 'Items added to cart! Proceed to checkout.')
    response = redirect('cart')
    response.set_cookie('product_ids', _cart_cookie_value(cart_ids))
    return response


# =============================================================
# FEATURE: COUPON / DISCOUNT CODES (ADMIN)
# =============================================================
@login_required(login_url='adminlogin')
def admin_coupon_list_view(request):
    coupons = models.Coupon.objects.all().order_by('-id')
    return render(request, 'ecom/admin_coupons.html', {'coupons': coupons})

@login_required(login_url='adminlogin')
def admin_add_coupon_view(request):
    couponForm = forms.CouponForm()
    if request.method == 'POST':
        couponForm = forms.CouponForm(request.POST)
        if couponForm.is_valid():
            couponForm.save()
            messages.success(request, 'Coupon created successfully!')
            return redirect('admin-coupons')
    return render(request, 'ecom/admin_add_coupon.html', {'couponForm': couponForm})

@login_required(login_url='adminlogin')
def admin_delete_coupon_view(request, pk):
    models.Coupon.objects.filter(id=pk).delete()
    messages.success(request, 'Coupon deleted.')
    return redirect('admin-coupons')


# =============================================================
# FEATURE: APPLY COUPON (CUSTOMER CHECKOUT)
# =============================================================
@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def apply_coupon_view(request):
    import datetime as dt
    code = request.POST.get('coupon_code', '').strip()
    redirect_url = request.POST.get('redirect_to', '/customer-address')
    try:
        coupon = models.Coupon.objects.get(code__iexact=code, active=True)
        today = dt.date.today()
        if coupon.expiry and coupon.expiry < today:
            messages.error(request, 'This coupon has expired.')
        else:
            coupon.usage_count = coupon.usage_count + 1
            coupon.save()
            request.session['coupon_code'] = coupon.code
            request.session['coupon_discount'] = coupon.discount_percent
            messages.success(request, 'Coupon applied! ' + str(coupon.discount_percent) + '% discount.')
    except models.Coupon.DoesNotExist:
        messages.error(request, 'Invalid coupon code.')
    return redirect(redirect_url)


# =============================================================
# FEATURE: SALES REPORT (DATE RANGE)
# =============================================================
@login_required(login_url='adminlogin')
def admin_sales_report_view(request):
    from django.utils import timezone
    import datetime
    import json
    from django.db.models import Count, Sum
    
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    orders = models.Order.objects.all().order_by('-order_date')
    if from_date:
        orders = orders.filter(order_date__gte=from_date)
    if to_date:
        orders = orders.filter(order_date__lte=to_date)
    total_revenue = sum(o.total_amount for o in orders if o.total_amount and o.is_revenue_ready)
    total_orders = orders.count()
    
    # Graph 1: Order Status Distribution
    status_counts = models.Order.objects.values('status').annotate(total=Count('id'))
    status_labels = [item['status'] for item in status_counts]
    status_data = [item['total'] for item in status_counts]

    # Graph 2: Last 7 Days Revenue (Only Delivered Orders)
    today = timezone.now().date()
    seven_days_ago = today - datetime.timedelta(days=6)
    start_date_7 = timezone.make_aware(datetime.datetime.combine(seven_days_ago, datetime.time.min))
    end_date_7 = timezone.make_aware(datetime.datetime.combine(today, datetime.time.max))

    recent_delivered = models.Order.objects.filter(
        status='Delivered',
        order_date__gte=start_date_7,
        order_date__lte=end_date_7
    )
    revenue_chart_labels = [(seven_days_ago + datetime.timedelta(days=i)).strftime('%b %d') for i in range(7)]
    revenue_dict = {}
    for obj in recent_delivered:
        if obj.is_revenue_ready:
            date_label = timezone.localtime(obj.order_date).strftime('%b %d')
            revenue_dict[date_label] = revenue_dict.get(date_label, 0) + (obj.total_amount or 0)
    revenue_chart_data = [revenue_dict.get(label, 0) for label in revenue_chart_labels]

    return render(request, 'ecom/admin_sales_report.html', {
        'orders': orders,
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'from_date': from_date or '',
        'to_date': to_date or '',
        'status_labels': json.dumps(status_labels),
        'status_data': json.dumps(status_data),
        'revenue_labels': json.dumps(revenue_chart_labels),
        'revenue_data': json.dumps(revenue_chart_data),
    })


# =============================================================
# FEATURE: BULK ORDER STATUS UPDATE
# =============================================================
@login_required(login_url='adminlogin')
def admin_bulk_update_status_view(request):
    if request.method == 'POST':
        order_ids = request.POST.getlist('order_ids')
        new_status = request.POST.get('new_status')
        valid_statuses = [s[0] for s in models.Order.STATUS]
        if new_status in valid_statuses and order_ids:
            if new_status == 'Cancelled':
                for oid in order_ids:
                    order = models.Order.objects.get(id=oid)
                    # Avoid double restoring if it was already cancelled
                    if order.status != 'Cancelled':
                        for item in order.items.all():
                            item.product.stock += item.quantity
                            item.product.save()
            
            models.Order.objects.filter(id__in=order_ids).update(status=new_status)
            if new_status == 'Delivered':
                from django.utils import timezone
                models.Order.objects.filter(id__in=order_ids, delivered_date__isnull=True).update(delivered_date=timezone.now())
            messages.success(request, str(len(order_ids)) + ' order(s) updated to "' + new_status + '".')
        else:
            messages.error(request, 'Please select at least one order and a valid status.')
    return redirect('admin-view-booking')


# =============================================================
# FEATURE: EXPORT ORDERS TO CSV
# =============================================================
import csv

@login_required(login_url='adminlogin')
def export_orders_csv_view(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=orders.csv'
    writer = csv.writer(response)
    writer.writerow(['Order ID', 'Customer', 'Email', 'Mobile', 'Address', 'Status', 'Total Amount', 'Order Date'])
    for order in models.Order.objects.all().order_by('-id'):
        writer.writerow([
            order.id,
            order.customer.get_name if order.customer else 'N/A',
            order.email or '',
            order.mobile or '',
            order.address or '',
            order.status or '',
            order.total_amount or 0,
            order.order_date or '',
        ])
    return response


# =============================================================
# FEATURE: COMPLAINT PAGE
# =============================================================
from django.contrib.auth.decorators import login_required, user_passes_test

@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def submit_complaint_view(request):
    customer = models.Customer.objects.get(user_id=request.user.id)
    complaintForm = forms.ComplaintForm()
    if request.method == 'POST':
        complaintForm = forms.ComplaintForm(request.POST)
        if complaintForm.is_valid():
            complaint = complaintForm.save(commit=False)
            complaint.customer = customer
            complaint.save()
            messages.success(request, 'Your complaint has been submitted successfully. We will review it shortly.')
            return redirect('my-complaints')
    product_count_in_cart = _cart_item_count(request)
    return render(request, 'ecom/submit_complaint.html', {
        'complaintForm': complaintForm,
        'product_count_in_cart': product_count_in_cart,
    })


@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def my_complaints_view(request):
    customer = models.Customer.objects.get(user_id=request.user.id)
    complaints = models.Complaint.objects.filter(customer=customer).order_by('-created_on')
    product_count_in_cart = _cart_item_count(request)
    return render(request, 'ecom/my_complaints.html', {
        'complaints': complaints,
        'product_count_in_cart': product_count_in_cart,
    })


@login_required(login_url='adminlogin')
def admin_view_complaints_view(request):
    complaints = models.Complaint.objects.all().select_related('customer', 'product').order_by('-created_on')
    feedbacks = models.Feedback.objects.all().order_by('-id')
    return render(request, 'ecom/admin_complaints.html', {'complaints': complaints, 'feedbacks': feedbacks})


@login_required(login_url='adminlogin')
def update_complaint_status_view(request, pk):
    if request.method == 'POST':
        complaint = models.Complaint.objects.get(id=pk)
        new_status = request.POST.get('status')
        if new_status in dict(models.Complaint.STATUS_CHOICES):
            complaint.status = new_status
            complaint.save()
            messages.success(request, 'Complaint status updated.')
    return redirect('admin-complaints')


# =============================================================
# COUPON: TOGGLE ACTIVE / DISABLE
# =============================================================
from django.contrib.auth.decorators import login_required

@login_required(login_url='adminlogin')
def admin_toggle_coupon_view(request, pk):
    from ecom import models
    from django.contrib import messages
    from django.shortcuts import redirect
    coupon = models.Coupon.objects.get(id=pk)
    coupon.active = not coupon.active
    coupon.save()
    status = 'enabled' if coupon.active else 'disabled'
    messages.success(request, 'Coupon "' + coupon.code + '" has been ' + status + '.')
    return redirect('admin-coupons')


# =============================================================
# FEATURE: SEARCH AUTOCOMPLETE
# =============================================================
from django.http import JsonResponse

def search_autocomplete_view(request):
    import json
    query = request.GET.get('term', '')
    data = []
    if query:
        # Search in name - prioritize matches at start of string or start of words
        # This prevents 'phone' from suggesting 'headphone'
        products = models.Product.objects.filter(
            Q(name__istartswith=query) | Q(name__icontains=' ' + query)
        )[:6]
        for p in products:
            img = p.product_image.url if p.product_image else '/static/images/success.png'
            data.append({
                'id': p.id,
                'name': p.name,
                'price': f"₹{p.price}",
                'image': img
            })
    return JsonResponse(data, safe=False)


@login_required(login_url='customerlogin')
def payment_view(request):
    if 'remove_coupon' in request.GET:
        request.session.pop('coupon_code', None)
        request.session.pop('coupon_discount', None)
        return redirect('payment')

    total=0
    quantity_map = _cart_quantity_map(request)
    if quantity_map:
        products = models.Product.objects.filter(id__in=quantity_map.keys())
        for p in products:
            total += p.price * quantity_map.get(p.id, 0)

    # Apply coupon discount if one is stored in session
    discount = request.session.get('coupon_discount', 0)
    original_total = total
    if discount:
        total = int(total - (total * discount / 100))
    
    response = render(request, 'ecom/payment.html', {
        'total': total,
        'original_total': original_total,
        'discount': discount,
        'discount_amount': original_total - total,
        'coupon_code': request.session.get('coupon_code', ''),
        'product_count_in_cart': _cart_item_count(request),
    })
    response.set_cookie('discounted_total', str(total))
    return response
