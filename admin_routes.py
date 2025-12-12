"""
Admin routes for web-based admin panel
"""
from flask import Blueprint, render_template_string, request, jsonify, redirect, url_for
import os
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from models import db, Subscriber, ScheduledMessage, Subscription, DepositApproval, SubscriptionPlan, DiscountCode, ServiceGroup
from plan_manager import get_active_plans, get_plan_by_id, validate_discount_code, apply_discount_code, increment_discount_code_usage
from sms_sender import send_sms_to_subscriber
from crypto_manager import activate_crypto_subscription
from telegram_bot import send_telegram_notification
from delivery_messages import get_delivery_message, create_delivery_message
from datetime import datetime, timedelta, timezone

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Simple HTML template for admin panel
ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel - Subscription Service</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header p { opacity: 0.9; }
        .nav {
            background: #f8f9fa;
            padding: 15px 30px;
            border-bottom: 2px solid #e9ecef;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }
        .nav button {
            padding: 10px 20px;
            border: none;
            background: white;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.3s;
            border: 2px solid transparent;
        }
        .nav button:hover {
            background: #667eea;
            color: white;
            transform: translateY(-2px);
        }
        .nav button.active {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }
        .content {
            padding: 30px;
        }
        .section {
            display: none;
        }
        .section.active {
            display: block;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        .stat-card h3 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .stat-card p {
            opacity: 0.9;
            font-size: 1.1em;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }
        th {
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }
        td {
            padding: 12px 15px;
            border-bottom: 1px solid #e9ecef;
        }
        tr:hover {
            background: #f8f9fa;
        }
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }
        .badge-active { background: #28a745; color: white; }
        .badge-pending { background: #ffc107; color: #333; }
        .badge-cancelled { background: #dc3545; color: white; }
        .badge-inactive { background: #6c757d; color: white; }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.3s;
            margin: 2px;
        }
        .btn-primary { background: #667eea; color: white; }
        .btn-primary:hover { background: #5568d3; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-danger:hover { background: #c82333; }
        .btn-success { background: #28a745; color: white; }
        .btn-success:hover { background: #218838; }
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
        }
        .form-group input, .form-group textarea, .form-group select {
            width: 100%;
            padding: 10px;
            border: 2px solid #e9ecef;
            border-radius: 6px;
            font-size: 1em;
        }
        .form-group input:focus, .form-group textarea:focus, .form-group select:focus {
            outline: none;
            border-color: #667eea;
        }
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        .modal.active {
            display: flex;
        }
        .modal-content {
            background: white;
            padding: 30px;
            border-radius: 12px;
            max-width: 500px;
            width: 90%;
            max-height: 90vh;
            overflow-y: auto;
        }
        .close {
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
            color: #999;
        }
        .close:hover { color: #333; }
        .alert {
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 20px;
        }
        .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .search-box {
            margin-bottom: 20px;
        }
        .search-box input {
            width: 100%;
            padding: 12px;
            border: 2px solid #e9ecef;
            border-radius: 6px;
            font-size: 1em;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛠️ Admin Panel</h1>
            <p>Subscription Service Management</p>
        </div>
        <div class="nav">
            <button onclick="showSection('dashboard')" class="active">📊 Dashboard</button>
            <button onclick="showSection('subscribers')">👥 Subscribers</button>
            <button onclick="showSection('messages')">📨 Messages</button>
            <button onclick="showSection('send')">✉️ Send Message</button>
            <button onclick="showSection('schedule')">📅 Schedule Message</button>
            <button onclick="showSection('deposits')">💰 Deposit Approvals</button>
            <button onclick="showSection('plans')">📦 Plans</button>
            <button onclick="showSection('codes')">🎫 Discount Codes</button>
            <button onclick="location.reload()">🔄 Refresh</button>
        </div>
        <div class="content">
            <div id="dashboard" class="section active">
                <h2>Dashboard</h2>
                <div id="stats-container"></div>
            </div>
            <div id="subscribers" class="section">
                <h2>Subscribers</h2>
                <div class="search-box">
                    <input type="text" id="subscriber-search" placeholder="Search subscribers..." onkeyup="filterSubscribers()">
                </div>
                <div id="subscribers-container"></div>
            </div>
            <div id="messages" class="section">
                <h2>Scheduled Messages</h2>
                <div id="messages-container"></div>
            </div>
            <div id="send" class="section">
                <h2>Send Message</h2>
                <form id="send-form" onsubmit="sendMessage(event)" enctype="multipart/form-data">
                    <div class="form-group">
                        <label>Subscriber ID</label>
                        <input type="number" id="send-subscriber-id" required>
                    </div>
                    <div class="form-group">
                        <label>Message</label>
                        <textarea id="send-message" rows="5" required></textarea>
                    </div>
                    <div class="form-group">
                        <label>Image (Optional) - Upload photo to send with message</label>
                        <input type="file" id="send-image" accept="image/*">
                        <small style="color: #6c757d; display: block; margin-top: 5px;">
                            📷 Supported: JPG, PNG, GIF. Max 5MB. For MMS via Twilio or email attachment.
                        </small>
                    </div>
                    <div class="form-group">
                        <label>Or Image URL (Optional)</label>
                        <input type="url" id="send-image-url" placeholder="https://example.com/image.jpg">
                        <small style="color: #6c757d; display: block; margin-top: 5px;">
                            Enter a publicly accessible image URL instead of uploading
                        </small>
                    </div>
                    <button type="submit" class="btn btn-primary">Send Message</button>
                </form>
                <div id="send-result"></div>
            </div>
            <div id="schedule" class="section">
                <h2>Schedule Message</h2>
                <form id="schedule-form" onsubmit="scheduleMessage(event)">
                    <div class="form-group">
                        <label>Subscriber ID</label>
                        <input type="number" id="schedule-subscriber-id" required>
                    </div>
                    <div class="form-group">
                        <label>Message</label>
                        <textarea id="schedule-message" rows="5" required></textarea>
                    </div>
                    <div class="form-group">
                        <label>Date & Time</label>
                        <input type="datetime-local" id="schedule-time" required>
                    </div>
                    <button type="submit" class="btn btn-primary">Schedule Message</button>
                </form>
                <p style="margin-top: 10px; color: #6c757d; font-size: 0.95em;">
                    Scheduled time is interpreted in the subscriber's local timezone.
                </p>
                <div id="schedule-result"></div>
            </div>
            <div id="deposits" class="section">
                <h2>💰 Deposit Approvals</h2>
                <div id="deposits-container"></div>
            </div>
            <div id="plans" class="section">
                <h2>📦 Subscription Plans</h2>
                <button onclick="showPlanModal()" class="btn btn-primary" style="margin-bottom: 20px;">➕ Add New Plan</button>
                <div id="plans-container"></div>
            </div>
            <div id="codes" class="section">
                <h2>🎫 Discount Codes</h2>
                <button onclick="showCodeModal()" class="btn btn-primary" style="margin-bottom: 20px;">➕ Generate New Code</button>
                <div id="codes-container"></div>
            </div>
        </div>
    </div>

    <!-- Plan Modal -->
    <div id="planModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closePlanModal()">&times;</span>
            <h2 id="planModalTitle">Add New Plan</h2>
            <form id="planForm" onsubmit="savePlan(event)">
                <input type="hidden" id="plan-id">
                <div class="form-group">
                    <label>Plan Name *</label>
                    <input type="text" id="plan-name" required>
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea id="plan-description" rows="3"></textarea>
                </div>
                <div class="form-group">
                    <label>Price (USD) *</label>
                    <input type="number" id="plan-price" step="0.01" min="0" required>
                </div>
                <div class="form-group">
                    <label>Currency</label>
                    <input type="text" id="plan-currency" value="USD">
                </div>
                <div class="form-group">
                    <label>Trial Days (0 = no trial)</label>
                    <input type="number" id="plan-trial-days" min="0" value="0">
                </div>
                <div class="form-group">
                    <label>Display Order</label>
                    <input type="number" id="plan-display-order" min="0" value="0">
                </div>
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="plan-is-active" checked> Active
                    </label>
                </div>
                <button type="submit" class="btn btn-primary">Save Plan</button>
                <button type="button" class="btn btn-secondary" onclick="closePlanModal()">Cancel</button>
            </form>
        </div>
    </div>

    <!-- Code Modal -->
    <div id="codeModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeCodeModal()">&times;</span>
            <h2 id="codeModalTitle">Generate Discount Code</h2>
            <form id="codeForm" onsubmit="saveCode(event)">
                <input type="hidden" id="code-id">
                <div class="form-group">
                    <label>Code *</label>
                    <input type="text" id="code-code" required style="text-transform: uppercase;">
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea id="code-description" rows="2"></textarea>
                </div>
                <div class="form-group">
                    <label>Discount Type *</label>
                    <select id="code-discount-type" required onchange="updateDiscountType()">
                        <option value="percent">Percentage (%)</option>
                        <option value="fixed">Fixed Amount ($)</option>
                    </select>
                </div>
                <div class="form-group">
                    <label id="code-value-label">Discount Value (%) *</label>
                    <input type="number" id="code-discount-value" step="0.01" min="0" max="100" required>
                </div>
                <div class="form-group">
                    <label>Max Uses (leave empty for unlimited)</label>
                    <input type="number" id="code-max-uses" min="1">
                </div>
                <div class="form-group">
                    <label>Valid From (optional)</label>
                    <input type="datetime-local" id="code-valid-from">
                </div>
                <div class="form-group">
                    <label>Valid Until (optional)</label>
                    <input type="datetime-local" id="code-valid-until">
                </div>
                <div class="form-group">
                    <label>Applicable Plan IDs (comma-separated, leave empty for all plans)</label>
                    <input type="text" id="code-plan-ids" placeholder="1,2,3">
                </div>
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="code-is-active" checked> Active
                    </label>
                </div>
                <button type="submit" class="btn btn-primary">Save Code</button>
                <button type="button" class="btn btn-secondary" onclick="closeCodeModal()">Cancel</button>
            </form>
        </div>
    </div>

    <!-- Code Validation Modal -->
    <div id="validateModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeValidateModal()">&times;</span>
            <h2>Validate Discount Code</h2>
            <form id="validateForm" onsubmit="validateCode(event)">
                <div class="form-group">
                    <label>Code *</label>
                    <input type="text" id="validate-code" required style="text-transform: uppercase;">
                </div>
                <div class="form-group">
                    <label>Plan ID (optional)</label>
                    <input type="number" id="validate-plan-id" min="1">
                </div>
                <button type="submit" class="btn btn-primary">Validate</button>
                <button type="button" class="btn btn-secondary" onclick="closeValidateModal()">Close</button>
            </form>
            <div id="validate-result" style="margin-top: 20px;"></div>
        </div>
    </div>

    <script>
        function showSection(sectionId) {
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.nav button').forEach(b => b.classList.remove('active'));
            document.getElementById(sectionId).classList.add('active');
            event.target.classList.add('active');
            
            if (sectionId === 'dashboard') loadDashboard();
            else if (sectionId === 'subscribers') loadSubscribers();
            else if (sectionId === 'messages') loadMessages();
            else if (sectionId === 'deposits') loadDeposits();
            else if (sectionId === 'plans') loadPlans();
            else if (sectionId === 'codes') loadCodes();
        }

        function getBadgeClass(status) {
            if (status === 'active') return 'badge-active';
            if (status === 'pending') return 'badge-pending';
            if (status === 'cancelled' || status === 'canceled') return 'badge-cancelled';
            return 'badge-inactive';
        }

        function formatUtcOffset(offsetMinutes) {
            if (offsetMinutes === null || offsetMinutes === undefined) offsetMinutes = 0;
            const sign = offsetMinutes >= 0 ? '+' : '-';
            const absMinutes = Math.abs(offsetMinutes);
            const hours = Math.floor(absMinutes / 60).toString().padStart(2, '0');
            const minutes = (absMinutes % 60).toString().padStart(2, '0');
            return `UTC${sign}${hours}:${minutes}`;
        }

        function formatTimezone(label, offsetMinutes) {
            const offsetText = formatUtcOffset(offsetMinutes);
            if (label && label !== 'UTC') {
                return `${label} (${offsetText})`;
            }
            return offsetText;
        }

        async function loadDashboard() {
            try {
                const response = await fetch('/admin/api/stats');
                const data = await response.json();
                
                const statsHtml = `
                    <div class="stats-grid">
                        <div class="stat-card">
                            <h3>${data.total_subscribers}</h3>
                            <p>Total Subscribers</p>
                        </div>
                        <div class="stat-card">
                            <h3>${data.active_subscribers}</h3>
                            <p>Active</p>
                        </div>
                        <div class="stat-card">
                            <h3>${data.pending_subscribers}</h3>
                            <p>Pending</p>
                        </div>
                        <div class="stat-card">
                            <h3>${data.total_messages}</h3>
                            <p>Total Messages</p>
                        </div>
                        <div class="stat-card">
                            <h3>${data.pending_messages}</h3>
                            <p>Pending Messages</p>
                        </div>
                        <div class="stat-card">
                            <h3>${data.stripe_count}</h3>
                            <p>Stripe Payments</p>
                        </div>
                        <div class="stat-card">
                            <h3>${data.paypal_count}</h3>
                            <p>PayPal Payments</p>
                        </div>
                        <div class="stat-card">
                            <h3>${data.crypto_count}</h3>
                            <p>Crypto Payments</p>
                        </div>
                    </div>
                `;
                document.getElementById('stats-container').innerHTML = statsHtml;
            } catch (error) {
                console.error('Error loading dashboard:', error);
            }
        }

        async function loadSubscribers() {
            try {
                const response = await fetch('/admin/api/subscribers');
                const subscribers = await response.json();
                
                if (subscribers.length === 0) {
                    document.getElementById('subscribers-container').innerHTML = '<p>No subscribers found.</p>';
                    return;
                }
                
                let tableHtml = `
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Name</th>
                                <th>Phone</th>
                                <th>Carrier</th>
                                <th>Status</th>
                                <th>Payment</th>
                                <th>Timezone</th>
                                <th>Created</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="subscribers-table-body">
                `;
                
                subscribers.forEach(sub => {
                    const createdDate = sub.created_at ? new Date(sub.created_at).toLocaleDateString() : 'N/A';
                    const timezoneDisplay = formatTimezone(sub.timezone_label, sub.timezone_offset_minutes);
                    tableHtml += `
                        <tr data-subscriber-id="${sub.id}">
                            <td>${sub.id}</td>
                            <td>${sub.name || 'N/A'}</td>
                            <td>${sub.phone_number}</td>
                            <td>${sub.carrier}</td>
                            <td><span class="badge ${getBadgeClass(sub.subscription_status)}">${sub.subscription_status}</span></td>
                            <td>${sub.payment_method || 'N/A'}</td>
                            <td>${timezoneDisplay}</td>
                            <td>${createdDate}</td>
                            <td>
                                <button class="btn btn-primary" onclick="viewSubscriber(${sub.id})">View</button>
                                <button class="btn btn-success" onclick="sendToSubscriber(${sub.id})">Send</button>
                            </td>
                        </tr>
                    `;
                });
                
                tableHtml += '</tbody></table>';
                document.getElementById('subscribers-container').innerHTML = tableHtml;
            } catch (error) {
                console.error('Error loading subscribers:', error);
            }
        }

        function filterSubscribers() {
            const search = document.getElementById('subscriber-search').value.toLowerCase();
            const rows = document.querySelectorAll('#subscribers-table-body tr');
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(search) ? '' : 'none';
            });
        }

        async function loadMessages() {
            try {
                const response = await fetch('/admin/api/messages');
                const messages = await response.json();
                
                if (messages.length === 0) {
                    document.getElementById('messages-container').innerHTML = '<p>No scheduled messages found.</p>';
                    return;
                }
                
                let tableHtml = `
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Subscriber</th>
                                <th>Message</th>
                                <th>Scheduled Time</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                `;
                
                messages.forEach(msg => {
                    const timezoneDisplay = formatTimezone(msg.timezone_label, msg.timezone_offset_minutes);
                    let scheduledDate = 'N/A';
                    if (msg.scheduled_time_local) {
                        const localDate = new Date(msg.scheduled_time_local);
                        scheduledDate = `${localDate.toLocaleString()} (${timezoneDisplay})`;
                    } else if (msg.scheduled_time) {
                        const utcDate = new Date(msg.scheduled_time);
                        scheduledDate = `${utcDate.toLocaleString()} (${timezoneDisplay})`;
                    }
                    const status = msg.sent ? '<span class="badge badge-active">Sent</span>' : '<span class="badge badge-pending">Pending</span>';
                    tableHtml += `
                        <tr>
                            <td>${msg.id}</td>
                            <td>${msg.subscriber_name || `ID: ${msg.subscriber_id}`}</td>
                            <td>${msg.message.substring(0, 50)}${msg.message.length > 50 ? '...' : ''}</td>
                            <td>${scheduledDate}</td>
                            <td>${status}</td>
                        </tr>
                    `;
                });
                
                tableHtml += '</tbody></table>';
                document.getElementById('messages-container').innerHTML = tableHtml;
            } catch (error) {
                console.error('Error loading messages:', error);
            }
        }

        async function sendMessage(event) {
            event.preventDefault();
            const subscriberId = document.getElementById('send-subscriber-id').value;
            const message = document.getElementById('send-message').value;
            const imageFile = document.getElementById('send-image').files[0];
            const imageUrl = document.getElementById('send-image-url').value;
            
            try {
                // If image file is selected, upload it first
                let finalImageUrl = imageUrl;
                
                if (imageFile) {
                    // Upload image file
                    const formData = new FormData();
                    formData.append('image', imageFile);
                    
                    const uploadResponse = await fetch('/admin/api/upload-image', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (uploadResponse.ok) {
                        const uploadResult = await uploadResponse.json();
                        finalImageUrl = uploadResult.image_url;
                    } else {
                        const uploadError = await uploadResponse.json();
                        document.getElementById('send-result').innerHTML = `<div class="alert alert-error">Image upload failed: ${uploadError.error || 'Unknown error'}</div>`;
                        return;
                    }
                }
                
                // Send message with optional image
                const response = await fetch('/admin/api/send-message', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        subscriber_id: subscriberId, 
                        message: message,
                        image_url: finalImageUrl || null
                    })
                });
                
                const result = await response.json();
                const resultDiv = document.getElementById('send-result');
                
                if (response.ok) {
                    const successMsg = result.message + (finalImageUrl ? ' 📷 (with image)' : '');
                    resultDiv.innerHTML = `<div class="alert alert-success">${successMsg}</div>`;
                    document.getElementById('send-form').reset();
                } else {
                    resultDiv.innerHTML = `<div class="alert alert-error">${result.error || 'Failed to send message'}</div>`;
                }
            } catch (error) {
                document.getElementById('send-result').innerHTML = `<div class="alert alert-error">Error: ${error.message}</div>`;
            }
        }

        async function scheduleMessage(event) {
            event.preventDefault();
            const subscriberId = document.getElementById('schedule-subscriber-id').value;
            const message = document.getElementById('schedule-message').value;
            const time = document.getElementById('schedule-time').value;
            
            try {
                const response = await fetch('/admin/api/schedule-message', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        subscriber_id: parseInt(subscriberId),
                        message: message,
                        scheduled_time: time
                    })
                });
                
                const result = await response.json();
                const resultDiv = document.getElementById('schedule-result');
                
                if (response.ok) {
                    resultDiv.innerHTML = `<div class="alert alert-success">${result.message}</div>`;
                    document.getElementById('schedule-form').reset();
                } else {
                    resultDiv.innerHTML = `<div class="alert alert-error">${result.error || 'Failed to schedule message'}</div>`;
                }
            } catch (error) {
                document.getElementById('schedule-result').innerHTML = `<div class="alert alert-error">Error: ${error.message}</div>`;
            }
        }

        function sendToSubscriber(id) {
            document.getElementById('send-subscriber-id').value = id;
            showSection('send');
        }

        async function viewSubscriber(id) {
            try {
                const response = await fetch(`/admin/api/subscribers/${id}`);
                const subscriber = await response.json();
                const timezoneDisplay = formatTimezone(subscriber.timezone_label, subscriber.timezone_offset_minutes);
                
                alert(`Subscriber Details:\n\nID: ${subscriber.id}\nName: ${subscriber.name}\nPhone: ${subscriber.phone_number}\nCarrier: ${subscriber.carrier}\nStatus: ${subscriber.subscription_status}\nPayment: ${subscriber.payment_method || 'N/A'}\nTimezone: ${timezoneDisplay}`);
            } catch (error) {
                alert('Error loading subscriber details');
            }
        }

        async function loadDeposits() {
            try {
                const response = await fetch('/admin/api/deposits');
                const deposits = await response.json();
                
                if (deposits.length === 0) {
                    document.getElementById('deposits-container').innerHTML = '<p>No pending deposit approvals found.</p>';
                    return;
                }
                
                let tableHtml = `
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Subscriber</th>
                                <th>Phone</th>
                                <th>Currency</th>
                                <th>Amount</th>
                                <th>TX Hash</th>
                                <th>Status</th>
                                <th>Created</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                `;
                
                deposits.forEach(deposit => {
                    const createdDate = deposit.created_at ? new Date(deposit.created_at).toLocaleString() : 'N/A';
                    const statusBadge = deposit.status === 'pending' 
                        ? '<span class="badge badge-pending">Pending</span>'
                        : deposit.status === 'approved'
                        ? '<span class="badge badge-active">Approved</span>'
                        : '<span class="badge badge-cancelled">Rejected</span>';
                    
                    // Show different action buttons based on type
                    let actionButtons = '';
                    if (deposit.status === 'pending') {
                        if (deposit.type === 'deposit_approval') {
                            actionButtons = `<button class="btn btn-success" onclick="approveDeposit(${deposit.id})">Approve</button>
                                           <button class="btn btn-danger" onclick="rejectDeposit(${deposit.id})">Reject</button>`;
                        } else if (deposit.type === 'pending_subscriber') {
                            actionButtons = `<button class="btn btn-success" onclick="approveSubscriber(${deposit.subscriber_id})">Approve</button>
                                           <button class="btn btn-danger" onclick="rejectSubscriber(${deposit.subscriber_id})">Reject</button>`;
                        }
                    }
                    
                    const typeLabel = deposit.type === 'deposit_approval' ? 'Manual' : (deposit.payment_type || 'Crypto');
                    const amountDisplay = deposit.amount > 0 ? `$${deposit.amount}` : (deposit.payment_type || 'N/A');
                    
                    tableHtml += `
                        <tr>
                            <td>${deposit.id}${deposit.type === 'pending_subscriber' ? ' (S)' : ''}</td>
                            <td>${deposit.subscriber_name || `ID: ${deposit.subscriber_id}`}</td>
                            <td>${deposit.subscriber_phone || 'N/A'}</td>
                            <td>${deposit.currency || typeLabel}</td>
                            <td>${amountDisplay}</td>
                            <td>${deposit.transaction_hash ? deposit.transaction_hash.substring(0, 20) + '...' : 'N/A'}</td>
                            <td>${statusBadge}</td>
                            <td>${createdDate}</td>
                            <td>${actionButtons}</td>
                        </tr>
                    `;
                });
                
                tableHtml += '</tbody></table>';
                document.getElementById('deposits-container').innerHTML = tableHtml;
            } catch (error) {
                console.error('Error loading deposits:', error);
                document.getElementById('deposits-container').innerHTML = '<div class="alert alert-error">Error loading deposits</div>';
            }
        }

        async function approveDeposit(id) {
            if (!confirm('Are you sure you want to approve this payment?')) return;
            
            try {
                const response = await fetch(`/admin/api/deposits/${id}/approve`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'}
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    alert('Payment approved successfully!');
                    loadDeposits();
                } else {
                    alert(`Error: ${result.error || 'Failed to approve payment'}`);
                }
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        }

        async function rejectDeposit(id) {
            const reason = prompt('Enter reason for rejection:');
            if (!reason) return;
            
            try {
                const response = await fetch(`/admin/api/deposits/${id}/reject`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({reason: reason})
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    alert('Payment rejected successfully!');
                    loadDeposits();
                } else {
                    alert(`Error: ${result.error || 'Failed to reject payment'}`);
                }
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        }

        async function approveSubscriber(subscriberId) {
            if (!confirm('Are you sure you want to approve this payment?')) return;
            
            try {
                const response = await fetch(`/admin/api/subscribers/${subscriberId}/approve-payment`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'}
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    alert('Payment approved successfully!');
                    loadDeposits();
                } else {
                    alert(`Error: ${result.error || 'Failed to approve payment'}`);
                }
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        }

        async function rejectSubscriber(subscriberId) {
            const reason = prompt('Enter reason for rejection:');
            if (!reason) return;
            
            try {
                const response = await fetch(`/admin/api/subscribers/${subscriberId}/reject-payment`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({reason: reason})
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    alert('Payment rejected successfully!');
                    loadDeposits();
                } else {
                    alert(`Error: ${result.error || 'Failed to reject payment'}`);
                }
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        }

        // ========== Plan Management Functions ==========
        
        async function loadPlans() {
            try {
                const response = await fetch('/admin/api/plans');
                const data = await response.json();
                
                if (!data.plans || data.plans.length === 0) {
                    document.getElementById('plans-container').innerHTML = '<p>No plans found. Create your first plan!</p>';
                    return;
                }
                
                let tableHtml = `
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Name</th>
                                <th>Price</th>
                                <th>Trial</th>
                                <th>Status</th>
                                <th>Order</th>
                                <th>Created</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                `;
                
                data.plans.forEach(plan => {
                    const trialText = plan.has_trial ? `${plan.trial_days} days` : 'No';
                    const statusBadge = plan.is_active 
                        ? '<span class="badge badge-active">Active</span>'
                        : '<span class="badge badge-inactive">Inactive</span>';
                    const createdDate = plan.created_at ? new Date(plan.created_at).toLocaleDateString() : 'N/A';
                    
                    tableHtml += `
                        <tr>
                            <td>${plan.id}</td>
                            <td><strong>${plan.name}</strong>${plan.description ? '<br><small>' + plan.description + '</small>' : ''}</td>
                            <td>$${plan.price.toFixed(2)} ${plan.currency}</td>
                            <td>${trialText}</td>
                            <td>${statusBadge}</td>
                            <td>${plan.display_order}</td>
                            <td>${createdDate}</td>
                            <td>
                                <button class="btn btn-primary" onclick="editPlan(${plan.id})">Edit</button>
                                <button class="btn btn-danger" onclick="deletePlanConfirm(${plan.id}, '${plan.name.replace(/'/g, "\\'")}')">Delete</button>
                            </td>
                        </tr>
                    `;
                });
                
                tableHtml += '</tbody></table>';
                document.getElementById('plans-container').innerHTML = tableHtml;
            } catch (error) {
                console.error('Error loading plans:', error);
                document.getElementById('plans-container').innerHTML = '<div class="alert alert-error">Error loading plans</div>';
            }
        }

        function showPlanModal(planId = null) {
            const modal = document.getElementById('planModal');
            const form = document.getElementById('planForm');
            const title = document.getElementById('planModalTitle');
            
            if (planId) {
                title.textContent = 'Edit Plan';
                fetch(`/admin/api/plans`)
                    .then(r => r.json())
                    .then(data => {
                        const plan = data.plans.find(p => p.id === planId);
                        if (plan) {
                            document.getElementById('plan-id').value = plan.id;
                            document.getElementById('plan-name').value = plan.name;
                            document.getElementById('plan-description').value = plan.description || '';
                            document.getElementById('plan-price').value = plan.price;
                            document.getElementById('plan-currency').value = plan.currency;
                            document.getElementById('plan-trial-days').value = plan.trial_days || 0;
                            document.getElementById('plan-display-order').value = plan.display_order || 0;
                            document.getElementById('plan-is-active').checked = plan.is_active;
                        }
                    });
            } else {
                title.textContent = 'Add New Plan';
                form.reset();
                document.getElementById('plan-id').value = '';
                document.getElementById('plan-currency').value = 'USD';
                document.getElementById('plan-trial-days').value = 0;
                document.getElementById('plan-display-order').value = 0;
                document.getElementById('plan-is-active').checked = true;
            }
            
            modal.style.display = 'block';
        }

        function closePlanModal() {
            document.getElementById('planModal').style.display = 'none';
        }

        async function savePlan(event) {
            event.preventDefault();
            
            const planId = document.getElementById('plan-id').value;
            const data = {
                name: document.getElementById('plan-name').value,
                description: document.getElementById('plan-description').value,
                price: parseFloat(document.getElementById('plan-price').value),
                currency: document.getElementById('plan-currency').value,
                trial_days: parseInt(document.getElementById('plan-trial-days').value) || 0,
                display_order: parseInt(document.getElementById('plan-display-order').value) || 0,
                is_active: document.getElementById('plan-is-active').checked
            };
            
            try {
                const url = planId ? `/admin/api/plans/${planId}` : '/admin/api/plans';
                const method = planId ? 'PUT' : 'POST';
                
                const response = await fetch(url, {
                    method: method,
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    alert(result.message || 'Plan saved successfully!');
                    closePlanModal();
                    loadPlans();
                } else {
                    alert(`Error: ${result.error || 'Failed to save plan'}`);
                }
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        }

        function editPlan(planId) {
            showPlanModal(planId);
        }

        async function deletePlanConfirm(planId, planName) {
            if (!confirm(`Are you sure you want to delete plan "${planName}"?\\n\\nThis action cannot be undone.`)) return;
            
            try {
                const response = await fetch(`/admin/api/plans/${planId}`, {
                    method: 'DELETE'
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    alert(result.message || 'Plan deleted successfully!');
                    loadPlans();
                } else {
                    alert(`Error: ${result.error || 'Failed to delete plan'}`);
                }
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        }

        // ========== Discount Code Management Functions ==========
        
        async function loadCodes() {
            try {
                const response = await fetch('/admin/api/codes');
                const data = await response.json();
                
                if (!data.codes || data.codes.length === 0) {
                    document.getElementById('codes-container').innerHTML = '<p>No discount codes found. Generate your first code!</p>';
                    return;
                }
                
                let tableHtml = `
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Code</th>
                                <th>Type</th>
                                <th>Value</th>
                                <th>Uses</th>
                                <th>Status</th>
                                <th>Valid Until</th>
                                <th>Created</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                `;
                
                data.codes.forEach(code => {
                    const discountDisplay = code.discount_type === 'percent' 
                        ? `${code.discount_value}%` 
                        : `$${code.discount_value.toFixed(2)}`;
                    const usesDisplay = code.max_uses 
                        ? `${code.current_uses}/${code.max_uses}` 
                        : `${code.current_uses}/∞`;
                    const statusBadge = code.is_active 
                        ? '<span class="badge badge-active">Active</span>'
                        : '<span class="badge badge-inactive">Inactive</span>';
                    const validUntil = code.valid_until 
                        ? new Date(code.valid_until).toLocaleDateString() 
                        : 'No expiry';
                    const createdDate = code.created_at ? new Date(code.created_at).toLocaleDateString() : 'N/A';
                    
                    tableHtml += `
                        <tr>
                            <td>${code.id}</td>
                            <td><strong>${code.code}</strong>${code.description ? '<br><small>' + code.description + '</small>' : ''}</td>
                            <td>${code.discount_type}</td>
                            <td>${discountDisplay}</td>
                            <td>${usesDisplay}</td>
                            <td>${statusBadge}</td>
                            <td>${validUntil}</td>
                            <td>${createdDate}</td>
                            <td>
                                <button class="btn btn-primary" onclick="editCode(${code.id})">Edit</button>
                                <button class="btn btn-info" onclick="showValidateModal('${code.code}')">Validate</button>
                                <button class="btn btn-danger" onclick="deleteCodeConfirm(${code.id}, '${code.code}')">Delete</button>
                            </td>
                        </tr>
                    `;
                });
                
                tableHtml += '</tbody></table>';
                document.getElementById('codes-container').innerHTML = tableHtml;
            } catch (error) {
                console.error('Error loading codes:', error);
                document.getElementById('codes-container').innerHTML = '<div class="alert alert-error">Error loading discount codes</div>';
            }
        }

        function showCodeModal(codeId = null) {
            const modal = document.getElementById('codeModal');
            const form = document.getElementById('codeForm');
            const title = document.getElementById('codeModalTitle');
            
            if (codeId) {
                title.textContent = 'Edit Discount Code';
                fetch(`/admin/api/codes`)
                    .then(r => r.json())
                    .then(data => {
                        const code = data.codes.find(c => c.id === codeId);
                        if (code) {
                            document.getElementById('code-id').value = code.id;
                            document.getElementById('code-code').value = code.code;
                            document.getElementById('code-description').value = code.description || '';
                            document.getElementById('code-discount-type').value = code.discount_type;
                            document.getElementById('code-discount-value').value = code.discount_value;
                            document.getElementById('code-max-uses').value = code.max_uses || '';
                            document.getElementById('code-valid-from').value = code.valid_from ? code.valid_from.substring(0, 16) : '';
                            document.getElementById('code-valid-until').value = code.valid_until ? code.valid_until.substring(0, 16) : '';
                            document.getElementById('code-plan-ids').value = code.applicable_plan_ids || '';
                            document.getElementById('code-is-active').checked = code.is_active;
                            updateDiscountType();
                        }
                    });
            } else {
                title.textContent = 'Generate Discount Code';
                form.reset();
                document.getElementById('code-id').value = '';
                document.getElementById('code-discount-type').value = 'percent';
                document.getElementById('code-is-active').checked = true;
                updateDiscountType();
            }
            
            modal.style.display = 'block';
        }

        function closeCodeModal() {
            document.getElementById('codeModal').style.display = 'none';
        }

        function updateDiscountType() {
            const type = document.getElementById('code-discount-type').value;
            const valueInput = document.getElementById('code-discount-value');
            const label = document.getElementById('code-value-label');
            
            if (type === 'percent') {
                label.textContent = 'Discount Value (%) *';
                valueInput.max = 100;
                valueInput.min = 0;
            } else {
                label.textContent = 'Discount Value ($) *';
                valueInput.removeAttribute('max');
                valueInput.min = 0;
            }
        }

        async function saveCode(event) {
            event.preventDefault();
            
            const codeId = document.getElementById('code-id').value;
            const data = {
                code: document.getElementById('code-code').value.toUpperCase(),
                description: document.getElementById('code-description').value,
                discount_type: document.getElementById('code-discount-type').value,
                discount_value: parseFloat(document.getElementById('code-discount-value').value),
                max_uses: document.getElementById('code-max-uses').value ? parseInt(document.getElementById('code-max-uses').value) : null,
                valid_from: document.getElementById('code-valid-from').value || null,
                valid_until: document.getElementById('code-valid-until').value || null,
                plan_ids: document.getElementById('code-plan-ids').value || null,
                is_active: document.getElementById('code-is-active').checked
            };
            
            try {
                const url = codeId ? `/admin/api/codes/${codeId}` : '/admin/api/codes';
                const method = codeId ? 'PUT' : 'POST';
                
                const response = await fetch(url, {
                    method: method,
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    alert(result.message || 'Code saved successfully!');
                    closeCodeModal();
                    loadCodes();
                } else {
                    alert(`Error: ${result.error || 'Failed to save code'}`);
                }
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        }

        function editCode(codeId) {
            showCodeModal(codeId);
        }

        async function deleteCodeConfirm(codeId, codeName) {
            if (!confirm(`Are you sure you want to delete discount code "${codeName}"?\\n\\nThis action cannot be undone.`)) return;
            
            try {
                const response = await fetch(`/admin/api/codes/${codeId}`, {
                    method: 'DELETE'
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    alert(result.message || 'Code deleted successfully!');
                    loadCodes();
                } else {
                    alert(`Error: ${result.error || 'Failed to delete code'}`);
                }
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        }

        function showValidateModal(code = '') {
            const modal = document.getElementById('validateModal');
            document.getElementById('validate-code').value = code;
            document.getElementById('validate-plan-id').value = '';
            document.getElementById('validate-result').innerHTML = '';
            modal.style.display = 'block';
        }

        function closeValidateModal() {
            document.getElementById('validateModal').style.display = 'none';
        }

        async function validateCode(event) {
            event.preventDefault();
            
            const code = document.getElementById('validate-code').value.toUpperCase();
            const planId = document.getElementById('validate-plan-id').value;
            
            const data = {
                code: code,
                plan_id: planId ? parseInt(planId) : null
            };
            
            try {
                const response = await fetch('/admin/api/codes/validate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                const resultDiv = document.getElementById('validate-result');
                
                if (result.valid) {
                    const code = result.code;
                    const discountDisplay = code.discount_type === 'percent' 
                        ? `${code.discount_value}%` 
                        : `$${code.discount_value.toFixed(2)}`;
                    const usesDisplay = code.max_uses 
                        ? `${code.current_uses}/${code.max_uses}` 
                        : `${code.current_uses}/∞`;
                    
                    resultDiv.innerHTML = `
                        <div class="alert alert-success">
                            <strong>✅ Valid Code!</strong><br>
                            Code: <strong>${code.code}</strong><br>
                            Type: ${code.discount_type}<br>
                            Value: ${discountDisplay}<br>
                            Uses: ${usesDisplay}<br>
                            Status: ${code.is_active ? 'Active' : 'Inactive'}<br>
                            ${code.valid_until ? 'Valid Until: ' + new Date(code.valid_until).toLocaleDateString() : 'No expiry'}
                        </div>
                    `;
                } else {
                    resultDiv.innerHTML = `
                        <div class="alert alert-error">
                            <strong>❌ Invalid Code</strong><br>
                            ${result.error || 'Code is not valid'}
                        </div>
                    `;
                }
            } catch (error) {
                document.getElementById('validate-result').innerHTML = `
                    <div class="alert alert-error">Error: ${error.message}</div>
                `;
            }
        }

        // Close modals when clicking outside
        window.onclick = function(event) {
            const planModal = document.getElementById('planModal');
            const codeModal = document.getElementById('codeModal');
            const validateModal = document.getElementById('validateModal');
            
            if (event.target === planModal) {
                closePlanModal();
            }
            if (event.target === codeModal) {
                closeCodeModal();
            }
            if (event.target === validateModal) {
                closeValidateModal();
            }
        }

        // Load dashboard on page load
        loadDashboard();
        // Auto-refresh every 30 seconds
        setInterval(() => {
            const activeSection = document.querySelector('.section.active');
            if (activeSection.id === 'dashboard') loadDashboard();
            else if (activeSection.id === 'subscribers') loadSubscribers();
            else if (activeSection.id === 'messages') loadMessages();
            else if (activeSection.id === 'deposits') loadDeposits();
            else if (activeSection.id === 'plans') loadPlans();
            else if (activeSection.id === 'codes') loadCodes();
        }, 30000);
    </script>
</body>
</html>
"""

@admin_bp.route('/')
def admin_panel():
    """Admin panel main page."""
    return render_template_string(ADMIN_TEMPLATE)

@admin_bp.route('/api/stats')
def get_stats():
    """Get statistics for dashboard."""
    total_subscribers = Subscriber.query.count()
    active_subscribers = Subscriber.query.filter_by(subscription_status='active').count()
    pending_subscribers = Subscriber.query.filter_by(subscription_status='pending').count()
    
    total_messages = ScheduledMessage.query.count()
    pending_messages = ScheduledMessage.query.filter_by(sent=False).count()
    
    stripe_count = Subscriber.query.filter_by(payment_method='stripe').count()
    paypal_count = Subscriber.query.filter_by(payment_method='paypal').count()
    crypto_count = Subscriber.query.filter_by(payment_method='crypto').count()
    
    return jsonify({
        'total_subscribers': total_subscribers,
        'active_subscribers': active_subscribers,
        'pending_subscribers': pending_subscribers,
        'total_messages': total_messages,
        'pending_messages': pending_messages,
        'stripe_count': stripe_count,
        'paypal_count': paypal_count,
        'crypto_count': crypto_count
    })

@admin_bp.route('/api/subscribers')
def get_subscribers_list():
    """Get all subscribers for admin panel."""
    subscribers = Subscriber.query.all()
    return jsonify([s.to_dict() for s in subscribers])

@admin_bp.route('/api/subscribers/<int:subscriber_id>')
def get_subscriber_detail(subscriber_id):
    """Get subscriber details."""
    subscriber = Subscriber.query.get_or_404(subscriber_id)
    return jsonify(subscriber.to_dict())

@admin_bp.route('/api/messages')
def get_messages_list():
    """Get all scheduled messages."""
    messages = ScheduledMessage.query.order_by(ScheduledMessage.scheduled_time.desc()).limit(100).all()
    result = []
    for msg in messages:
        subscriber = Subscriber.query.get(msg.subscriber_id)
        offset_minutes = msg.timezone_offset_minutes if msg.timezone_offset_minutes is not None else (subscriber.timezone_offset_minutes if subscriber and subscriber.timezone_offset_minutes is not None else 0)
        label = msg.timezone_label or (subscriber.timezone_label if subscriber and subscriber.timezone_label else 'UTC')
        scheduled_time_local = None
        if msg.scheduled_time:
            scheduled_time_local = (msg.scheduled_time + timedelta(minutes=offset_minutes or 0)).isoformat()
        result.append({
            'id': msg.id,
            'subscriber_id': msg.subscriber_id,
            'subscriber_name': subscriber.name if subscriber else None,
            'message': msg.message,
            'scheduled_time': msg.scheduled_time.isoformat() if msg.scheduled_time else None,
            'scheduled_time_local': scheduled_time_local,
            'timezone_offset_minutes': offset_minutes,
            'timezone_label': label,
            'sent': msg.sent,
            'sent_at': msg.sent_at.isoformat() if msg.sent_at else None
        })
    return jsonify(result)

@admin_bp.route('/api/send-message', methods=['POST'])
def admin_send_message():
    """Send message from admin panel."""
    from flask import current_app
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        subscriber_id = data.get('subscriber_id')
        message = data.get('message')
        image_url = data.get('image_url')  # Optional image URL
        
        if not subscriber_id or not message:
            return jsonify({'error': 'subscriber_id and message are required'}), 400
        
        # Convert subscriber_id to int if it's a string
        try:
            subscriber_id = int(subscriber_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid subscriber_id format'}), 400
        
        subscriber = Subscriber.query.get(subscriber_id)
        if not subscriber:
            return jsonify({'error': f'Subscriber with ID {subscriber_id} not found'}), 404
        
        # Validate subscriber has required fields
        if not subscriber.phone_number:
            return jsonify({'error': 'Subscriber phone number is missing'}), 400
        
        # Check if it's international number (needs Twilio) or US number (needs carrier)
        is_international = subscriber.phone_number.startswith('+') or len(subscriber.phone_number.replace('+', '').replace('-', '').replace(' ', '')) > 10
        
        if not is_international and not subscriber.carrier:
            return jsonify({
                'error': 'Subscriber carrier is missing. Required for US phone numbers.',
                'subscriber_id': subscriber.id,
                'phone_number': subscriber.phone_number
            }), 400
        
        # Validate message
        if not message or not message.strip():
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Check SMTP/Twilio configuration based on phone type
        if is_international:
            from config import Config
            if not Config.TWILIO_ACCOUNT_SID or not Config.TWILIO_AUTH_TOKEN:
                return jsonify({
                    'error': 'Twilio is not configured. Cannot send to international numbers.',
                    'phone_number': subscriber.phone_number,
                    'hint': 'Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in environment variables'
                }), 500
        else:
            from config import Config
            if not Config.SMTP_USERNAME or not Config.SMTP_PASSWORD:
                return jsonify({
                    'error': 'SMTP is not configured. Cannot send SMS via email.',
                    'phone_number': subscriber.phone_number,
                    'hint': 'Set SMTP_USERNAME and SMTP_PASSWORD in environment variables'
                }), 500
        
        # Try to send the message
        try:
            success = send_sms_to_subscriber(subscriber, message, image_url=image_url)
            if success:
                return jsonify({
                    'message': f'Message sent successfully to {subscriber.name or subscriber.phone_number}',
                    'subscriber_id': subscriber.id,
                    'phone_number': subscriber.phone_number,
                    'carrier': subscriber.carrier if not is_international else 'Twilio'
                })
            else:
                return jsonify({
                    'error': 'Failed to send message. Check server logs for details.',
                    'subscriber_id': subscriber.id,
                    'phone_number': subscriber.phone_number,
                    'hint': 'Check SMTP/Twilio configuration and network connectivity'
                }), 500
        except Exception as send_error:
            import traceback
            send_error_details = traceback.format_exc()
            print(f"Error sending SMS in admin_send_message: {send_error_details}")
            return jsonify({
                'error': f'Error sending message: {str(send_error)}',
                'subscriber_id': subscriber.id,
                'phone_number': subscriber.phone_number,
                'error_type': type(send_error).__name__
            }), 500
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in admin_send_message: {error_details}")
        return jsonify({
            'error': f'Server error: {str(e)}',
            'details': str(e)
        }), 500

@admin_bp.route('/api/schedule-group-messages', methods=['POST'])
def schedule_group_messages_endpoint():
    """Schedule group messages (morning/noon/evening) for all active subscribers."""
    from group_message_scheduler import schedule_group_messages, schedule_daily_group_messages
    
    data = request.get_json()
    group_id = data.get('group_id')
    message_type = data.get('message_type', 'morning')  # morning, noon, or evening
    message_text = data.get('message')  # Optional custom message
    date_str = data.get('date')  # Optional date (YYYY-MM-DD), defaults to today
    
    if not group_id:
        return jsonify({'error': 'group_id is required'}), 400
    
    try:
        # Parse date if provided
        date = None
        if date_str:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Schedule messages
        if message_type == 'all':
            # Schedule all three (morning, noon, evening)
            results = schedule_daily_group_messages(group_id, date=date)
            return jsonify({
                'message': 'All daily messages scheduled successfully',
                'results': results
            })
        else:
            # Schedule single message type
            result = schedule_group_messages(group_id, message_type, message_text, date=date)
            if 'error' in result:
                return jsonify(result), 404
            
            return jsonify({
                'message': f'{message_type.capitalize()} messages scheduled successfully',
                'scheduled': result['scheduled'],
                'timezone_matched': result['timezone_matched'],
                'non_timezone_matched': result['non_timezone_matched'],
                'message_type': message_type
            })
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error scheduling group messages: {error_details}")
        return jsonify({
            'error': f'Error scheduling group messages: {str(e)}'
        }), 500

@admin_bp.route('/api/upload-image', methods=['POST'])
def upload_image():
    """Upload image file for sending with messages."""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        if file_ext not in allowed_extensions:
            return jsonify({
                'error': f'Invalid file type. Allowed: {", ".join(allowed_extensions)}'
            }), 400
        
        # Check file size (max 5MB)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 5 * 1024 * 1024:  # 5MB
            return jsonify({'error': 'File too large. Maximum size is 5MB'}), 400
        
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        file_path = os.path.join(upload_dir, unique_filename)
        file.save(file_path)
        
        # For now, return the file path
        # In production, you might want to upload to a CDN or cloud storage
        # and return a public URL instead
        image_url = f"/admin/uploads/{unique_filename}"
        
        # Note: In production, upload to cloud storage (S3, Cloudinary, etc.)
        # and return the public URL instead of local file path
        
        return jsonify({
            'message': 'Image uploaded successfully',
            'image_url': image_url,
            'filename': unique_filename
        })
        
    except RequestEntityTooLarge:
        return jsonify({'error': 'File too large. Maximum size is 5MB'}), 400
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error uploading image: {error_details}")
        return jsonify({
            'error': f'Error uploading image: {str(e)}'
        }), 500

@admin_bp.route('/uploads/<filename>')
def serve_uploaded_image(filename):
    """Serve uploaded images."""
    from flask import send_from_directory
    upload_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads')
    return send_from_directory(upload_dir, filename)

@admin_bp.route('/api/schedule-message', methods=['POST'])
def admin_schedule_message():
    """Schedule message from admin panel."""
    data = request.get_json()
    subscriber_id = data.get('subscriber_id')
    message = data.get('message')
    scheduled_time_str = data.get('scheduled_time')
    
    if not subscriber_id or not message or not scheduled_time_str:
        return jsonify({'error': 'subscriber_id, message, and scheduled_time are required'}), 400
    
    subscriber = Subscriber.query.get(subscriber_id)
    if not subscriber:
        return jsonify({'error': 'Subscriber not found'}), 404
    
    try:
        # Parse datetime from ISO format
        parsed_time = datetime.fromisoformat(scheduled_time_str.replace('Z', '+00:00'))

        timezone_offset = subscriber.timezone_offset_minutes or 0
        timezone_label = subscriber.timezone_label or 'UTC'

        def format_offset(minutes: int) -> str:
            sign = '+' if minutes >= 0 else '-'
            minutes_abs = abs(minutes)
            hours = minutes_abs // 60
            mins = minutes_abs % 60
            return f"UTC{sign}{hours:02d}:{mins:02d}"

        # Check if subscriber wants timezone matching
        use_timezone_matching = subscriber.use_timezone_matching and subscriber.message_delivery_preference == 'scheduled_timezone'
        
        if parsed_time.tzinfo is not None:
            utc_time = parsed_time.astimezone(timezone.utc)
            local_display_time = (utc_time + timedelta(minutes=timezone_offset)).replace(tzinfo=None)
            utc_naive = utc_time.replace(tzinfo=None)
        else:
            # If timezone matching is enabled, treat the input time as local time
            if use_timezone_matching:
                # Input time is in subscriber's local timezone, convert to UTC
                local_display_time = parsed_time
                utc_naive = parsed_time - timedelta(minutes=timezone_offset)
            else:
                # Input time is already in UTC (no timezone matching)
                local_display_time = parsed_time
                utc_naive = parsed_time

        scheduled_msg = ScheduledMessage(
            subscriber_id=subscriber_id,
            message=message,
            scheduled_time=utc_naive,
            timezone_offset_minutes=timezone_offset,
            timezone_label=timezone_label
        )
        
        db.session.add(scheduled_msg)
        db.session.commit()
        
        timezone_display = format_offset(timezone_offset)
        if timezone_label and timezone_label != 'UTC':
            timezone_display = f"{timezone_label} ({timezone_display})"
        
        matching_status = "with timezone matching" if use_timezone_matching else "without timezone matching"
        
        return jsonify({
            'message': f'Message scheduled successfully for {local_display_time.strftime("%Y-%m-%d %H:%M:%S")} {timezone_display} ({matching_status})',
            'scheduled_message_id': scheduled_msg.id,
            'timezone_matched': use_timezone_matching
        })
    except ValueError as e:
        return jsonify({'error': f'Invalid date format: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/deposits')
def get_deposits():
    """Get all deposit approvals and pending crypto subscribers."""
    result = []
    
    # Get all DepositApproval records
    deposits = DepositApproval.query.order_by(DepositApproval.created_at.desc()).all()
    for deposit in deposits:
        subscriber = deposit.subscriber
        result.append({
            'id': deposit.id,
            'type': 'deposit_approval',
            'subscriber_id': deposit.subscriber_id,
            'subscriber_name': subscriber.name if subscriber else None,
            'subscriber_phone': subscriber.phone_number if subscriber else None,
            'currency': deposit.currency,
            'amount': float(deposit.amount) if deposit.amount else 0,
            'wallet_address': deposit.wallet_address,
            'transaction_hash': deposit.transaction_hash,
            'status': deposit.status,
            'admin_notes': deposit.admin_notes,
            'created_at': deposit.created_at.isoformat() if deposit.created_at else None,
            'reviewed_at': deposit.reviewed_at.isoformat() if deposit.reviewed_at else None
        })
    
    # Get pending crypto subscribers that don't have DepositApproval records
    pending_crypto_subscribers = Subscriber.query.filter_by(
        subscription_status='pending',
        payment_method='crypto'
    ).all()
    
    for subscriber in pending_crypto_subscribers:
        # Check if this subscriber already has a DepositApproval record
        has_deposit_approval = any(d.subscriber_id == subscriber.id for d in deposits)
        if not has_deposit_approval:
            # This is a pending crypto subscriber without DepositApproval (likely Coinbase Commerce)
            result.append({
                'id': subscriber.id,
                'type': 'pending_subscriber',
                'subscriber_id': subscriber.id,
                'subscriber_name': subscriber.name,
                'subscriber_phone': subscriber.phone_number,
                'currency': 'N/A',
                'amount': 0,  # Amount not stored in subscriber record
                'wallet_address': subscriber.crypto_payment_address or 'N/A',
                'transaction_hash': subscriber.crypto_transaction_hash,
                'status': 'pending',
                'admin_notes': None,
                'created_at': subscriber.created_at.isoformat() if subscriber.created_at else None,
                'reviewed_at': None,
                'payment_method': 'crypto',
                'payment_type': 'Coinbase Commerce' if subscriber.crypto_payment_address and not subscriber.crypto_payment_address.startswith('0x') and len(subscriber.crypto_payment_address) > 20 else 'Manual'
            })
    
    # Sort by created_at descending
    result.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    return jsonify(result)

@admin_bp.route('/api/deposits/<int:deposit_id>/approve', methods=['POST'])
def approve_deposit(deposit_id):
    """Approve a deposit."""
    try:
        deposit = DepositApproval.query.get_or_404(deposit_id)
        
        if deposit.status != 'pending':
            return jsonify({'error': f'Deposit is not pending (current status: {deposit.status})'}), 400
        
        subscriber = deposit.subscriber
        if not subscriber:
            return jsonify({'error': 'Subscriber not found'}), 404
        
        # Approve the deposit
        deposit.status = 'approved'
        deposit.reviewed_at = datetime.utcnow()
        deposit.reviewed_by = 'admin_panel'
        
        # Activate the subscription
        if subscriber.payment_method == 'crypto':
            activate_crypto_subscription(subscriber, deposit.transaction_hash)
        else:
            subscriber.subscription_status = 'active'
        
        db.session.commit()
        
        # Send Telegram notification if user has Telegram ID
        telegram_sent = False
        if subscriber.telegram_user_id:
            try:
                # Determine language (English only)
                language = 'en'
                
                # Send payment confirmation message
                confirmation_msg = get_delivery_message('payment_approved', language)
                if subscriber.name:
                    confirmation_msg = f"Hi {subscriber.name}!\n\n{confirmation_msg}"
                
                # Send welcome message
                welcome_msg = get_delivery_message('welcome', language)
                if subscriber.name:
                    welcome_msg = f"Hi {subscriber.name}!\n\n{welcome_msg}"
                
                # Send both messages
                send_telegram_notification(subscriber, confirmation_msg)
                send_telegram_notification(subscriber, welcome_msg)
                telegram_sent = True
                print(f"[INFO] Telegram messages sent to subscriber {subscriber.id} (Telegram ID: {subscriber.telegram_user_id})")
            except Exception as tg_error:
                print(f"[WARNING] Failed to send Telegram notification: {str(tg_error)}")
                # Don't fail the approval if Telegram fails
        
        return jsonify({
            'message': 'Payment approved successfully',
            'deposit_id': deposit.id,
            'subscriber_id': subscriber.id,
            'telegram_notification_sent': telegram_sent
        })
    except Exception as e:
        db.session.rollback()
        import traceback
        error_details = traceback.format_exc()
        print(f"Error approving deposit: {error_details}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/deposits/<int:deposit_id>/reject', methods=['POST'])
def reject_deposit(deposit_id):
    """Reject a deposit."""
    try:
        data = request.get_json() or {}
        reason = data.get('reason', 'Payment rejected by admin')
        
        deposit = DepositApproval.query.get_or_404(deposit_id)
        
        if deposit.status != 'pending':
            return jsonify({'error': f'Deposit is not pending (current status: {deposit.status})'}), 400
        
        subscriber = deposit.subscriber
        
        # Reject the deposit
        deposit.status = 'rejected'
        deposit.reviewed_at = datetime.utcnow()
        deposit.reviewed_by = 'admin_panel'
        deposit.admin_notes = reason
        
        # Update subscriber status
        if subscriber:
            subscriber.subscription_status = 'inactive'
        
        db.session.commit()
        
        return jsonify({
            'message': 'Payment rejected successfully',
            'deposit_id': deposit.id
        })
    except Exception as e:
        db.session.rollback()
        import traceback
        error_details = traceback.format_exc()
        print(f"Error rejecting deposit: {error_details}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/subscribers/<int:subscriber_id>/approve-payment', methods=['POST'])
def approve_subscriber_payment(subscriber_id):
    """Approve a pending subscriber payment."""
    try:
        subscriber = Subscriber.query.get_or_404(subscriber_id)
        
        if subscriber.subscription_status != 'pending':
            return jsonify({'error': f'Subscriber is not pending (current status: {subscriber.subscription_status})'}), 400
        
        subscriber.subscription_status = 'active'
        
        # Create or update subscription record
        from models import Subscription
        sub_record = Subscription.query.filter_by(
            subscriber_id=subscriber.id,
            payment_method=subscriber.payment_method
        ).first()
        
        if not sub_record:
            sub_record = Subscription(
                subscriber_id=subscriber.id,
                payment_method=subscriber.payment_method,
                status='active',
                current_period_start=datetime.utcnow(),
                current_period_end=datetime.utcnow() + timedelta(days=30)
            )
            
            # Add payment method specific IDs
            if subscriber.payment_method == 'stripe':
                sub_record.stripe_subscription_id = subscriber.stripe_subscription_id
                sub_record.stripe_customer_id = subscriber.stripe_customer_id
            elif subscriber.payment_method == 'paypal':
                sub_record.paypal_subscription_id = subscriber.paypal_subscription_id
                sub_record.paypal_billing_agreement_id = subscriber.paypal_billing_agreement_id
            elif subscriber.payment_method == 'crypto':
                sub_record.crypto_payment_id = subscriber.crypto_payment_address
                sub_record.crypto_transaction_hash = subscriber.crypto_transaction_hash
            
            db.session.add(sub_record)
        else:
            sub_record.status = 'active'
            sub_record.current_period_start = datetime.utcnow()
            sub_record.current_period_end = datetime.utcnow() + timedelta(days=30)
        
        db.session.commit()
        
        # Send Telegram notification if user has Telegram ID
        telegram_sent = False
        if subscriber.telegram_user_id:
            try:
                # Determine language (English only)
                language = 'en'
                
                # Send payment confirmation message
                confirmation_msg = get_delivery_message('payment_approved', language)
                if subscriber.name:
                    confirmation_msg = f"Hi {subscriber.name}!\n\n{confirmation_msg}"
                
                # Send welcome message
                welcome_msg = get_delivery_message('welcome', language)
                if subscriber.name:
                    welcome_msg = f"Hi {subscriber.name}!\n\n{welcome_msg}"
                
                # Send both messages
                send_telegram_notification(subscriber, confirmation_msg)
                send_telegram_notification(subscriber, welcome_msg)
                telegram_sent = True
                print(f"[INFO] Telegram messages sent to subscriber {subscriber.id} (Telegram ID: {subscriber.telegram_user_id})")
            except Exception as tg_error:
                print(f"[WARNING] Failed to send Telegram notification: {str(tg_error)}")
                # Don't fail the approval if Telegram fails
        
        return jsonify({
            'message': 'Payment approved successfully',
            'subscriber_id': subscriber.id,
            'status': 'active',
            'telegram_notification_sent': telegram_sent
        })
    except Exception as e:
        db.session.rollback()
        import traceback
        error_details = traceback.format_exc()
        print(f"Error approving subscriber payment: {error_details}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/subscribers/<int:subscriber_id>/reject-payment', methods=['POST'])
def reject_subscriber_payment(subscriber_id):
    """Reject a pending subscriber payment."""
    try:
        data = request.get_json() or {}
        reason = data.get('reason', 'Payment rejected by admin')
        
        subscriber = Subscriber.query.get_or_404(subscriber_id)
        
        if subscriber.subscription_status != 'pending':
            return jsonify({'error': f'Subscriber is not pending (current status: {subscriber.subscription_status})'}), 400
        
        subscriber.subscription_status = 'inactive'
        
        # Update subscription record if exists
        from models import Subscription
        sub_record = Subscription.query.filter_by(
            subscriber_id=subscriber.id,
            payment_method=subscriber.payment_method
        ).first()
        
        if sub_record:
            sub_record.status = 'cancelled'
        
        db.session.commit()
        
        return jsonify({
            'message': 'Payment rejected successfully',
            'subscriber_id': subscriber.id,
            'status': 'inactive',
            'reason': reason
        })
    except Exception as e:
        db.session.rollback()
        import traceback
        error_details = traceback.format_exc()
        print(f"Error rejecting subscriber payment: {error_details}")
        return jsonify({'error': str(e)}), 500

# ========== Plan Management API Endpoints ==========

@admin_bp.route('/api/plans', methods=['GET'])
def get_plans():
    """Get all subscription plans."""
    try:
        plans = SubscriptionPlan.query.order_by(SubscriptionPlan.display_order).all()
        return jsonify({
            'plans': [plan.to_dict() for plan in plans]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/plans', methods=['POST'])
def create_plan():
    """Create a new subscription plan."""
    try:
        data = request.get_json()
        
        # Validate required fields
        name = data.get('name')
        price = data.get('price')
        if not name:
            return jsonify({'error': 'Name is required'}), 400
        if price is None:
            # allow zero price (free/trial plans) so only None is treated as missing
            return jsonify({'error': 'Price is required'}), 400
        # Ensure price is numeric
        try:
            price = float(price)
        except (TypeError, ValueError):
            return jsonify({'error': 'Price must be a number'}), 400
        
        # Check if plan name already exists
        existing = SubscriptionPlan.query.filter_by(name=data['name']).first()
        if existing:
            return jsonify({'error': f"Plan with name '{data['name']}' already exists"}), 400
        
        plan = SubscriptionPlan(
            name=name,
            description=data.get('description'),
            price=price,
            currency=data.get('currency', 'USD'),
            has_trial=data.get('trial_days', 0) > 0,
            trial_days=data.get('trial_days', 0),
            is_active=data.get('is_active', True),
            display_order=data.get('display_order', 0)
        )
        
        db.session.add(plan)
        db.session.commit()
        
        return jsonify({
            'message': 'Plan created successfully',
            'plan': plan.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/plans/<int:plan_id>', methods=['PUT'])
def update_plan(plan_id):
    """Update a subscription plan."""
    try:
        plan = SubscriptionPlan.query.get(plan_id)
        if not plan:
            return jsonify({'error': 'Plan not found'}), 404
        
        data = request.get_json()
        
        if 'name' in data:
            # Check if new name conflicts with another plan
            existing = SubscriptionPlan.query.filter_by(name=data['name']).first()
            if existing and existing.id != plan.id:
                return jsonify({'error': f"Plan with name '{data['name']}' already exists"}), 400
            plan.name = data['name']
        
        if 'description' in data:
            plan.description = data['description']
        
        if 'price' in data:
            plan.price = data['price']
        
        if 'currency' in data:
            plan.currency = data['currency']
        
        if 'trial_days' in data:
            plan.has_trial = data['trial_days'] > 0
            plan.trial_days = data['trial_days']
        
        if 'is_active' in data:
            plan.is_active = data['is_active']
        
        if 'display_order' in data:
            plan.display_order = data['display_order']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Plan updated successfully',
            'plan': plan.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/plans/<int:plan_id>', methods=['DELETE'])
def delete_plan(plan_id):
    """Delete a subscription plan."""
    try:
        plan = SubscriptionPlan.query.get(plan_id)
        if not plan:
            return jsonify({'error': 'Plan not found'}), 404
        
        # Check if plan is being used
        subscribers_count = Subscriber.query.filter_by(plan_id=plan_id).count()
        if subscribers_count > 0:
            return jsonify({
                'error': f"Cannot delete plan - it is being used by {subscribers_count} subscriber(s)"
            }), 400
        
        plan_name = plan.name
        db.session.delete(plan)
        db.session.commit()
        
        return jsonify({
            'message': f'Plan "{plan_name}" deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ========== Discount Code Management API Endpoints ==========

@admin_bp.route('/api/codes', methods=['GET'])
def get_codes():
    """Get all discount codes."""
    try:
        codes = DiscountCode.query.order_by(DiscountCode.created_at.desc()).all()
        return jsonify({
            'codes': [code.to_dict() for code in codes]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/codes', methods=['POST'])
def create_code():
    """Create a new discount code."""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('code') or not data.get('discount_type') or data.get('discount_value') is None:
            return jsonify({'error': 'Code, discount_type, and discount_value are required'}), 400
        
        # Check if code already exists
        existing = DiscountCode.query.filter_by(code=data['code'].upper()).first()
        if existing:
            return jsonify({'error': f"Discount code '{data['code'].upper()}' already exists"}), 400
        
        # Validate discount value
        if data['discount_type'] == 'percent' and (data['discount_value'] < 0 or data['discount_value'] > 100):
            return jsonify({'error': 'Percentage discount must be between 0 and 100'}), 400
        
        if data['discount_type'] == 'fixed' and data['discount_value'] < 0:
            return jsonify({'error': 'Fixed discount cannot be negative'}), 400
        
        # Parse validity dates
        valid_from = None
        valid_until = None
        if data.get('valid_from'):
            valid_from = datetime.fromisoformat(data['valid_from'].replace('Z', '+00:00'))
        if data.get('valid_until'):
            valid_until = datetime.fromisoformat(data['valid_until'].replace('Z', '+00:00'))
        
        code = DiscountCode(
            code=data['code'].upper(),
            description=data.get('description'),
            discount_type=data['discount_type'],
            discount_value=data['discount_value'],
            max_uses=data.get('max_uses'),
            valid_from=valid_from,
            valid_until=valid_until,
            is_active=data.get('is_active', True),
            applicable_plan_ids=data.get('plan_ids')
        )
        
        db.session.add(code)
        db.session.commit()
        
        return jsonify({
            'message': 'Discount code created successfully',
            'code': code.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/codes/<int:code_id>', methods=['PUT'])
def update_code(code_id):
    """Update a discount code."""
    try:
        code = DiscountCode.query.get(code_id)
        if not code:
            return jsonify({'error': 'Discount code not found'}), 404
        
        data = request.get_json()
        
        if 'code' in data:
            # Check if new code conflicts with another code
            existing = DiscountCode.query.filter_by(code=data['code'].upper()).first()
            if existing and existing.id != code.id:
                return jsonify({'error': f"Discount code '{data['code'].upper()}' already exists"}), 400
            code.code = data['code'].upper()
        
        if 'description' in data:
            code.description = data['description']
        
        if 'discount_type' in data:
            code.discount_type = data['discount_type']
        
        if 'discount_value' in data:
            # Validate discount value
            discount_type = data.get('discount_type', code.discount_type)
            if discount_type == 'percent' and (data['discount_value'] < 0 or data['discount_value'] > 100):
                return jsonify({'error': 'Percentage discount must be between 0 and 100'}), 400
            if discount_type == 'fixed' and data['discount_value'] < 0:
                return jsonify({'error': 'Fixed discount cannot be negative'}), 400
            code.discount_value = data['discount_value']
        
        if 'max_uses' in data:
            code.max_uses = data['max_uses']
        
        if 'valid_from' in data:
            code.valid_from = datetime.fromisoformat(data['valid_from'].replace('Z', '+00:00')) if data['valid_from'] else None
        
        if 'valid_until' in data:
            code.valid_until = datetime.fromisoformat(data['valid_until'].replace('Z', '+00:00')) if data['valid_until'] else None
        
        if 'is_active' in data:
            code.is_active = data['is_active']
        
        if 'plan_ids' in data:
            code.applicable_plan_ids = data['plan_ids'] if data['plan_ids'] else None
        
        db.session.commit()
        
        return jsonify({
            'message': 'Discount code updated successfully',
            'code': code.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/codes/<int:code_id>', methods=['DELETE'])
def delete_code(code_id):
    """Delete a discount code."""
    try:
        code = DiscountCode.query.get(code_id)
        if not code:
            return jsonify({'error': 'Discount code not found'}), 404
        
        code_name = code.code
        db.session.delete(code)
        db.session.commit()
        
        return jsonify({
            'message': f'Discount code "{code_name}" deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/codes/validate', methods=['POST'])
def validate_code():
    """Validate a discount code."""
    try:
        data = request.get_json()
        code_text = data.get('code', '').upper()
        plan_id = data.get('plan_id')
        
        if not code_text:
            return jsonify({'error': 'Code is required'}), 400
        
        is_valid, discount_code, error_msg = validate_discount_code(code_text, plan_id)
        
        if not is_valid:
            return jsonify({
                'valid': False,
                'error': error_msg
            }), 200
        
        return jsonify({
            'valid': True,
            'code': discount_code.to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

