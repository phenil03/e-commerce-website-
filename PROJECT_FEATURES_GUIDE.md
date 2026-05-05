# 📘 Project Features & Functionality Guide

This document provides a comprehensive breakdown of all the features implemented in the **ECOHENIL** e-commerce platform. It is designed to help developers and users understand the capabilities of both the **Customer-facing** and **Admin-facing** panels.

---

## 👥 Customer-Side Features

### 1. Authentication & Account Management
*   **Sign-Up & Login**: Secure registration and login for customers.
*   **Forgot Password**: A simple yet effective password recovery system using username and first-name verification.
*   **Profile Management**: Customers can view and edit their personal details, including profile pictures, mobile numbers, and shipping addresses.

### 2. Product Discovery
*   **Smart Search**:
    *   **Synonym Support**: Searching for "phone" also finds "smartphone", "iphone", and "android".
    *   **Exclusion Logic**: Prevents unrelated items (like phone cases) from appearing when searching for the main device.
    *   **Autocomplete**: Real-time suggestions as you type in the search bar.
*   **Category Navigation**: Products are grouped into categories like Electronics, Fashion, Home, and more.
*   **Product Details**: Deep-dive views for products, featuring descriptions parsed into specifications and bullet points.

### 3. Shopping Experience
*   **Cart System**: 
    *   Add/remove items with a single click.
    *   **Purchase Limits**: Maximum of 5 units per product to prevent bulk-buying.
    *   **Stock Check**: Automatically prevents adding items that are out of stock.
*   **Wishlist**: Save your favorite products for future purchases.
*   **Reorder Utility**: One-click reordering of previous purchases to save time.

### 4. Checkout & Payments
*   **Saved Addresses**: shipping addresses are saved to the profile for faster checkout next time.
*   **Flexible Payments**: Support for **Credit/Debit Card** and **Cash on Delivery (COD)**.
*   **Invoices**: Generate and download professional PDF-style invoices for every successful order.

### 5. Post-Purchase & Support
*   **Order Tracking**: Monitor orders through stages: Pending → Confirmed → Out for Delivery → Delivered.
*   **Return System**: A dedicated 7-day return window for delivered items. Customers must provide a reason for the return.
*   **Reviews & Ratings**: Rate products (1-5 stars) and leave comments to help other shoppers.
*   **Complaint Portal**: A structured way to report issues regarding delivery or product quality.
*   **Feedback**: Direct communication line to the site administrator.

---

## 🛠️ Admin-Side Features

### 1. Advanced Analytics Dashboard
*   **Live Overview**: Instant access to total customer count, product count, and active orders.
*   **Revenue Tracking**: Real-time calculation of today's revenue based on delivered orders.
*   **Trend Graphs**:
    *   **Order Status**: Visual breakdown of Pending vs. Delivered orders.
    *   **Sales Trends**: 15-day revenue charts to monitor growth.
    *   **Category Performance**: Identify which categories are generating the most revenue.

### 2. Inventory & Product Management
*   **CRUD Operations**: Full control to Create, Read, Update, and Delete products.
*   **Stock Alerts**: Integrated warnings for products with low stock (5 or fewer units).
*   **Automatic Stock Control**: The system automatically restores stock when an order is cancelled or a return is approved.

### 3. Order & Fulfillment
*   **Order Management**: View and update the status of every order in the system.
*   **Bulk Updates**: Select multiple orders and update their status (e.g., mark as 'Confirmed') in one go.
*   **Returns & Refunds**: Review return requests, approve/reject them, and track refund completion.
*   **Data Export**: Download the entire order history as a **CSV file** for offline accounting.

### 4. Customer Support Management
*   **Complaint Handling**: View and update the status of customer complaints (Pending → Reviewed → Resolved).
*   **Feedback Monitoring**: Read all customer feedback in a centralized list.
*   **Coupon Factory**: Create, delete, or temporarily disable discount codes.

---

## ⚙️ Core System Logic (Internal)
*   **Revenue Integrity**: Revenue is only counted for "Delivered" orders and is deducted if a return is processed.
*   **Middleware Protection**: Ensures only authorized users (Admin vs Customer) can access their respective panels.
*   **Database**: Utilizes Django's ORM for high-performance queries and data integrity.

---

*This project is built with a focus on usability, clean code, and premium aesthetics.*
