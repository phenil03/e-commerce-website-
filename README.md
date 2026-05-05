# 🛒 ECOHENIL v2.0 - Advanced E-Commerce Platform

![Django](https://img.shields.io/badge/Django-4.2-092E20?style=for-the-badge&logo=django&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![UI/UX](https://img.shields.io/badge/UI%2FUX-Premium-FF69B4?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

Welcome to **ECOHENIL**, a robust and feature-rich e-commerce application built with Django. This platform is designed to provide a seamless shopping experience for customers and a comprehensive management dashboard for administrators.

---

## 🌟 Key Features

### 👤 Customer Experience
*   **Intuitive Shopping**: Browse and search products across multiple categories (Electronics, Fashion, Home, etc.).
*   **Wishlist & Cart**: Save items for later or add them to your cart with persistent session management.
*   **Advanced Checkout**: Secure checkout process with support for **Card** and **Cash on Delivery (COD)**.
*   **Order Tracking**: Real-time status updates (Pending → Confirmed → Out for Delivery → Delivered).
*   **Return System**: Hassle-free 7-day return policy for delivered items.
*   **Reviews & Ratings**: Share feedback and rate products from 1 to 5 stars.
*   **Invoices**: Automatically generated downloadable invoices for every successful order.
  
*   **Complaint Portal**: Submit and track complaints regarding products or delivery.

### 🛡️ Admin Management
*   **Analytics Dashboard**: Visual overview of total customers, product sales, and real-time revenue tracking.
*   **Inventory Control**: Easily add, update, or remove products with stock management.
*   **Order Fulfillment**: Manage lifecycle of orders, including return requests and refunds.
*   **Customer Support**: Monitor feedback and resolve customer complaints directly from the dashboard.
*   **Marketing Tools**: Create and manage active coupons and discount percentages.

---

## 🛠️ Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Backend** | Python 3.10+ & Django 4.2 |
| **Database** | SQLite (Default) / PostgreSQL Ready |
| **Frontend** | HTML5, CSS3, Vanilla JS |
| **Auth** | Django Built-in Authentication |
| **Image Handling** | Pillow (Python Imaging Library) |

---

## 🚀 Getting Started

Follow these steps to get the project running on your local machine.

### 1. Prerequisites
Ensure you have **Python 3.10 or higher** installed.

### 2. Clone the Repository
```bash
git clone https://github.com/phenil03/e-commerce-website-.git
cd e-commerce-website-
```

### 3. Setup Virtual Environment
```bash
# Create environment
python -m venv .venv

# Activate environment (Windows)
.venv\Scripts\activate

# Activate environment (Mac/Linux)
source .venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirement.txt
```

### 5. Initialize Database
```bash
python manage.py migrate
```

### 6. Create Admin Account (Optional)
```bash
python manage.py createsuperuser
```

### 7. Run the Application
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` in your browser to start shopping!

---

## 📂 Project Structure

```text
├── ecommerce/          # Project settings and configuration
├── ecom/               # Core application logic (Models, Views, Forms)
├── static/             # CSS, JavaScript, and Image assets
├── templates/          # HTML Templates for Customer and Admin panels
├── manage.py           # Django management script
└── requirement.txt     # List of required Python packages
```

---

## 📸 Visuals
Check the `static/screenshots/` folder for a glimpse of the UI:
- **Customer Homepage**: `homepage.png`
- **Admin Dashboard**: `admin_dashboard.png`

---

## 🤝 Support & Feedback
We love hearing from you! If you encounter any bugs or have suggestions for new features, please open an issue on the repository.

**Made with ❤️ for a better shopping experience.**
