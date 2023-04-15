import frappe
from datetime import datetime
from frappe.utils import cstr
import requests

base_url = cstr(frappe.local.site)
application_url = ""
if "localhost" in base_url:
    application_url = f"http://{base_url}:8000"
else:
    application_url = f"https://{base_url}"

firebase_whatsapp_url = "https://asia-south1-backendfunction-23ae0.cloudfunctions.net/sendWhatsappMsgTextNoTemplate"

def create_sales_order_from_invoices(allInvoiceItems):
    post_data = {
                    "doctype": "Sales Order",
                    "customer": "Suchitra Inc",
                    "status": "Closed",
                    "items": allInvoiceItems
                }
    sales_order_url = f"{application_url}/api/resource/Sales Order"
    response = requests.post(url=sales_order_url, json=post_data, headers={
        "Authorization": "token 77bf05a96431e7b:468aa438ed17f6f"
    })
    sales_order_name = response.json().get("data").get("name")
    sales_submit_url = f"{application_url}/api/resource/Sales Order/{sales_order_name}"
    response = requests.post(url=sales_submit_url, json={"run_method": "submit"}, headers={
        "Authorization": "token 77bf05a96431e7b:468aa438ed17f6f"
    })

def send_whatsapp_message(msg_content, recievers, names):
    for i in range(len(recievers)):
        new_msg_content = msg_content.replace("###INSERT_NAME###", names[i])
        message_request_body = {
            "to": f"91{recievers[i]}",
            "preview_url": True,
            "message_content": new_msg_content
        }
        response = requests.post(url=firebase_whatsapp_url, json=message_request_body)

def prepare_all_customers_whatsapp_message(customer_mapping):
    all_customers = customer_mapping.keys()
    whatsapp_message_content = "Hi ###INSERT_NAME###,\nDaily Sales Stats\n"
    for customer in all_customers:
        whatsapp_message_content += f"{customer} : ₹{customer_mapping[customer]}\n"
    whatsapp_message_content += f"For more details Please visit {application_url}/app"
    return whatsapp_message_content

def sales_invoice_to_order():
    all_invoice_items = []
    date = datetime.today().strftime('%d-%m-%Y')
    year_format_date = datetime.today().strftime('%Y-%m-%d')
    present_invoices = frappe.get_all('Sales Invoice', filters={'is_pos': 1, 'posting_date':date}, fields={'name', 'posting_date', 'customer'})
    customer_to_invoice_mapping = {}
    customer_managers = []
    for invoice in present_invoices:
        invoice_doc = frappe.get_doc("Sales Invoice", invoice.name)
        if invoice_doc.customer not in customer_to_invoice_mapping:
            customer_to_invoice_mapping[invoice_doc.customer] = 0
        for invoice_item in invoice_doc.items:
            customer_to_invoice_mapping[invoice_doc.customer] += invoice_item.amount
            all_invoice_items.append({
                "item_code": invoice_item.item_code,
                "qty": invoice_item.qty,
                "rate": invoice_item.rate,
                "delivery_date": year_format_date,
                "amount": invoice_item.amount
            })
    whatsapp_message_recievers = []
    whatsapp_name_recievers = []
    main_message_recievers = frappe.get_all("User", filters={'role': 'Main Whatsapp Reciever'}, fields={'email', 'name'})
    for main_user in main_message_recievers:
        contact_doc = frappe.get_all("Contact", filters={'user': main_user.name}, fields={'mobile_no', 'name'})
        if len(contact_doc) > 0 and contact_doc[0].mobile_no is not None and contact_doc[0].mobile_no is not '':
            whatsapp_message_recievers.append(contact_doc[0].mobile_no)
            whatsapp_name_recievers.append(contact_doc[0].name)
    send_whatsapp_message(prepare_all_customers_whatsapp_message(customer_to_invoice_mapping), whatsapp_message_recievers, whatsapp_name_recievers)
    for customer in customer_to_invoice_mapping.keys():
        customer_doc = frappe.get_doc("Customer", customer)
        if customer_doc.account_manager:
            user_doc = frappe.get_doc("User", customer_doc.account_manager)
            contact_doc = frappe.get_all("Contact", filters={'user': user_doc.name}, fields={'mobile_no', 'name'})
            if len(contact_doc) > 0 and contact_doc[0].mobile_no is not None and contact_doc[0].mobile_no is not '':
                dummy_mapping = {}
                dummy_mapping[customer] = customer_to_invoice_mapping[customer]
                send_whatsapp_message(prepare_all_customers_whatsapp_message(dummy_mapping), [contact_doc[0].mobile_no],[contact_doc[0].name])