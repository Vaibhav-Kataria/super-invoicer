import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import os
import time
import uuid
import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import base64
from PIL import Image as PILImage
################ External EXcel Trial Below
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
# Define the scope
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Load from secrets
service_account_info = st.secrets["gcp_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)

################ External EXcel Trial Above

# Set page configuration
st.set_page_config(page_title="Invoice Generator", layout="wide")

# Function to load product data
@st.cache_data
def load_product_data(file_path="products.xlsx"):
    # try:
    #     return pd.read_excel(file_path)
    # except FileNotFoundError:
    # Create sample product data if file doesn't exist
    sample_data = {
        'product_id': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21],
        'product_name': ['Toilet Cleaner 5L','Handwash 5L','Glass Cleaner 5L','Floor Cleaner 5L','Shampoo 20ml Bottles','Shampoo 30ml Bottles','Shampoo 5L','Shower Gel 20ml Bottles','Shower Gel 30ml Bottles','Shower Gel 5L','Moisturiser 20ml Bottles','Moisturiser 30ml Bottles','Conditioner 20ml Bottles','Conditioner 30ml Bottles','Air Freshener 300ml','Air Freshener 5L','Samples','Liquid Soap Dispensers','Soap 10gms','Soap 15gms','Soap 20gms'],            
        'product_tax_rate': [0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
        'product_mrp':[500,500,500,500,6,8,800,6,8,800,7,9,7,9,149,2000,0,400,4.6,5.4,6],
        'product_default_discount':[10,50,50,50,25,25,50,25,50,50,50,50,50,50,50,50,50,50,50,50,50]
    }
    df = pd.DataFrame(sample_data)
    df.to_excel("products.xlsx", index=False)
    return df

# Function to calculate price based on MRP and discount
def calculate_price(mrp, discount_percentage):
    return mrp * (1 - discount_percentage / 100)

# Function to load invoice data
def load_invoice_data(file_path="inglo_delhi_invoices.xlsx"):
    try:
        return pd.read_excel(file_path)
    except FileNotFoundError:
        # Create empty invoice dataframe with appropriate columns
        df = pd.DataFrame(columns=[
            'invoice_id', 'date', 'customer_name', 'customer_email', 
            'customer_phone', 'customer_address', 'products', 'quantities',
            'mrps', 'discount_percentages', 'prices', 'subtotal', 'tax', 'total'
        ])
        df.to_excel("invoices.xlsx", index=False)
        return df

# Function to load company settings
def load_company_settings(file_path="inglo_delhi_company_settings.json"):
    import json
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Default settings
        default_settings = {
            "company_name": "Inglo Imex Private Limited",
            "company_address": "Sector 8 Dwarka, New Delhi 110077",
            "company_phone": "(+91) 87006-01262",
            "company_email": "ingloimexsales@gmail.com",
            "company_website": "www.yourcompany.com",
            "company_logo_path": None,
            "invoice_terms": "Payment is due within 30 days of the order date."
        }
        with open(file_path, 'w') as f:
            json.dump(default_settings, f, indent=4)
        return default_settings

# Function to save company settings
def save_company_settings(settings, file_path="inglo_delhi_company_settings.json"):
    import json
    with open(file_path, 'w') as f:
        json.dump(settings, f, indent=4)
    return True

# Function to generate invoice ID
def generate_invoice_id():
    # Generate ID based on timestamp + short random string for uniqueness
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = str(uuid.uuid4())[:4]
    return f"INV-{timestamp}-{unique_id}"

# Function to save invoice data
def save_invoice(invoice_data, file_path="inglo_delhi_invoices.xlsx"):
    existing_invoices = load_invoice_data(file_path)
    updated_invoices = pd.concat([existing_invoices, pd.DataFrame([invoice_data])], ignore_index=True)
    updated_invoices.to_excel(file_path, index=False)
    return True

# Function to create PDF invoice
def create_pdf_invoice(invoice_data, selected_products, company_settings):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        rightMargin=72, 
        leftMargin=72,
        topMargin=72, 
        bottomMargin=72
    )
    
    styles = getSampleStyleSheet()
    elements = []
    
    # Create custom styles
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=1,  # Center alignment
        spaceAfter=12
    )
    
    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=6
    )
    
    normal_style = styles["Normal"]
    normal_right = ParagraphStyle(
        'NormalRight', 
        parent=normal_style,
        alignment=2  # Right alignment
    )
    
    # Create company header table with logo if available
    header_data = []
    company_info = [
        [Paragraph(f"<b>{company_settings['company_name']}</b>", normal_style)],
        [Paragraph(company_settings['company_address'].replace('\n', '<br/>'), normal_style)],
        [Paragraph(f"Phone: {company_settings['company_phone']}", normal_style)],
        [Paragraph(f"Email: {company_settings['company_email']}", normal_style)],
        [Paragraph(f"Website: {company_settings['company_website']}", normal_style)]
    ]
    
    if company_settings['company_logo_path'] and os.path.exists(company_settings['company_logo_path']):
        # Add logo
        logo = Image(company_settings['company_logo_path'], width=2*inch, height=1*inch)
        header_data = [
            [logo, Table(company_info, colWidths=[3*inch])]
        ]
    else:
        header_data = [
            [Table(company_info, colWidths=[5*inch])]
        ]
    
    header_table = Table(header_data, colWidths=[2*inch, 3*inch])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.25*inch))
    
    # Add invoice title
    elements.append(Paragraph("INVOICE", title_style))
    elements.append(Spacer(1, 0.25*inch))
    
    # Add invoice details in a table
    invoice_info_data = [
        ["Invoice #:", invoice_data['invoice_id']],
        ["Date:", invoice_data['date']],
        ["Due Date:", (datetime.strptime(invoice_data['date'].split()[0], "%Y-%m-%d") + 
                      pd.Timedelta(days=30)).strftime("%Y-%m-%d")]
    ]
    
    invoice_info_table = Table(invoice_info_data, colWidths=[1.5*inch, 4*inch])
    invoice_info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(invoice_info_table)
    elements.append(Spacer(1, 0.25*inch))
    
    # Billing and customer info in a side by side table
    billing_data = [
        [Paragraph("<b>Billed To:</b>", normal_style), ""],
        [invoice_data['customer_name'], ""],
        [invoice_data['customer_email'], ""],
        [invoice_data['customer_phone'], ""],
        [invoice_data['customer_address'], ""]
    ]
    
    billing_table = Table(billing_data, colWidths=[3*inch, 2.5*inch])
    billing_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(billing_table)
    elements.append(Spacer(1, 0.25*inch))
    
    # Items table - Updated to include MRP and Discount columns
    items_data = [["Item", "MRP", "Discount %", "Price", "Quantity", "Tax", "Amount"]]
    
    for item in selected_products:
        items_data.append([
            item['product_name'],
            f"INR {item['mrp']:.2f}",
            f"{item['discount_percentage']:.1f}%",
            f"INR {item['price']:.2f}",
            str(item['quantity']),
            f"INR {item['tax_amount']:.2f}",
            f"INR {item['amount']:.2f}"
        ])
    
    # Add totals row
    items_data.append(["", "", "", "", "", "Subtotal:", f"INR {invoice_data['subtotal']:.2f}"])
    items_data.append(["", "", "", "", "", "Tax Total:", f"INR {invoice_data['tax']:.2f}"])
    items_data.append(["", "", "", "", "", "Total:", f"INR {invoice_data['total']:.2f}"])
    
    items_table = Table(items_data, colWidths=[1.8*inch, 0.9*inch, 0.8*inch, 0.9*inch, 0.7*inch, 0.7*inch, 0.9*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -4), colors.beige),
        ('BACKGROUND', (5, -3), (-1, -1), colors.beige),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -4), 1, colors.black),
        ('LINEABOVE', (5, -3), (-1, -3), 1, colors.black),
        ('LINEABOVE', (5, -1), (-1, -1), 1, colors.black),
        ('LINEBELOW', (5, -1), (-1, -1), 1, colors.black),
        ('FONTNAME', (5, -1), (5, -1), 'Helvetica-Bold'),
        ('FONTNAME', (6, -1), (6, -1), 'Helvetica-Bold'),
    ]))
    elements.append(items_table)
    
    # Add footer with terms and conditions
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph("<b>Terms & Conditions</b>", normal_style))
    elements.append(Paragraph(company_settings['invoice_terms'], normal_style))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

# Function to create download link for PDF
def get_pdf_download_link(pdf_bytes, filename):
    b64 = base64.b64encode(pdf_bytes.read()).decode()
    return f'<a href="data:application/pdf;base64,{b64}" download="{filename}">Download Invoice PDF</a>'

def main():
    st.title("💼 Invoice Generator")
    
    # Load company settings
    company_settings = load_company_settings()
    
    # Add a tab control for main app and settings
    tab1, tab2 = st.tabs(["📝 Invoice Generator", "⚙️ Company Settings"])
    
    with tab1:
        # Load product data
        product_df = load_product_data()
        
        # Sidebar for customer information
        st.sidebar.header("Customer Information")
        customer_name = st.sidebar.text_input("Customer Name")
        customer_email = st.sidebar.text_input("Customer Email")
        customer_phone = st.sidebar.text_input("Customer Phone")
        customer_address = st.sidebar.text_area("Customer Address")
        
        # Product selection section
        st.header("Select Products")
        
        # Create columns for product selection interface
        col1, col2, col3, col4, col5, col6 = st.columns([2.5, 0.8, 0.8, 0.8, 0.8, 1])
        
        with col1:
            st.subheader("Product")
        with col2:
            st.subheader("MRP")
        with col3:
            st.subheader("Discount %")
        with col4:
            st.subheader("Price")
        with col5:
            st.subheader("Quantity")
        with col6:
            st.subheader("Amount")
        
        # Initialize session state for selected products if not exists
        if 'selected_products' not in st.session_state:
            st.session_state.selected_products = []
        
        # Initialize session state for current invoice
        if 'current_invoice' not in st.session_state:
            st.session_state.current_invoice = None
        
        # Add new product row
        with st.form(key="add_product_form"):
            col1, col2, col3, col4, col5, col6 = st.columns([2.5, 0.8, 0.8, 0.8, 0.8, 1])
            
            with col1:
                product = st.selectbox("Select Product", product_df['product_name'].tolist())
            
            # Get product details
            product_info = product_df[product_df['product_name'] == product].iloc[0]
            
            with col2:
                mrp = st.number_input("MRP", value=float(product_info['product_mrp']), disabled=True, key="mrp_display")
            
            with col3:
                discount_percentage = st.number_input("Discount", 
                                                    value=float(product_info['product_default_discount']), 
                                                    min_value=0.0, 
                                                    max_value=100.0, 
                                                    step=0.1,
                                                    help="Enter discount percentage (without % sign)")
            
            # Calculate price based on MRP and discount
            calculated_price = calculate_price(mrp, discount_percentage)
            
            with col4:
                st.text(f"₹{calculated_price:.2f}")
            
            with col5:
                quantity = st.number_input("Quantity", min_value=1, value=1)
            
            with col6:
                amount = calculated_price * quantity
                st.text(f"₹{amount:.2f}")
            
            add_product_submitted = st.form_submit_button("Add Product")
            
            if add_product_submitted:
                # Add product to session state
                tax_rate = float(product_info['product_tax_rate'])
                st.session_state.selected_products.append({
                    'product_id': product_info['product_id'],
                    'product_name': product,
                    'mrp': mrp,
                    'discount_percentage': discount_percentage,
                    'price': calculated_price,
                    'quantity': quantity,
                    'tax_rate': tax_rate,
                    'tax_amount': calculated_price * quantity * tax_rate,
                    'amount': calculated_price * quantity
                })
                st.success(f"Added {quantity} x {product} at ₹{calculated_price:.2f} each ({discount_percentage}% discount)")
                # Force a rerun to update the product list display
                st.rerun()
        
        # Show selected products
        if st.session_state.selected_products:
            st.header("Selected Products")
            
            for i, item in enumerate(st.session_state.selected_products):
                cols = st.columns([2.5, 0.8, 0.8, 0.8, 0.8, 1, 0.5])
                cols[0].text(item['product_name'])
                cols[1].text(f"₹{item['mrp']:.2f}")
                cols[2].text(f"{item['discount_percentage']:.1f}%")
                cols[3].text(f"₹{item['price']:.2f}")
                cols[4].text(f"{item['quantity']}")
                cols[5].text(f"₹{item['amount']:.2f}")
                
                # Remove button for each product
                if cols[6].button("✕", key=f"remove_{i}"):
                    st.session_state.selected_products.pop(i)
                    st.rerun()
            
            # Calculate totals
            subtotal = sum(item['amount'] for item in st.session_state.selected_products)
            tax_total = sum(item['tax_amount'] for item in st.session_state.selected_products)
            total = subtotal + tax_total
            
            # Display summary
            st.header("Invoice Summary")
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Invoice Date:**", datetime.now().strftime("%Y-%m-%d"))
                st.write("**Customer Name:**", customer_name if customer_name else "Not specified")
                st.write("**Customer Email:**", customer_email if customer_email else "Not specified")
            
            with col2:
                st.write("**Subtotal:**", f"₹{subtotal:.2f}")
                st.write("**Tax:**", f"₹{tax_total:.2f}")
                st.write("**Total Amount:**", f"₹{total:.2f}")
            
            # Generate invoice button
            if st.button("Generate Invoice", type="primary"):
                if not customer_name:
                    st.error("Please enter customer name")
                else:
                    # Generate invoice ID
                    invoice_id = generate_invoice_id()
                    
                    # Prepare invoice data
                    invoice_data = {
                        'invoice_id': invoice_id,
                        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'customer_name': customer_name,
                        'customer_email': customer_email,
                        'customer_phone': customer_phone,
                        'customer_address': customer_address,
                        'products': str([item['product_name'] for item in st.session_state.selected_products]),
                        'quantities': str([item['quantity'] for item in st.session_state.selected_products]),
                        'mrps': str([item['mrp'] for item in st.session_state.selected_products]),
                        'discount_percentages': str([item['discount_percentage'] for item in st.session_state.selected_products]),
                        'prices': str([item['price'] for item in st.session_state.selected_products]),
                        'subtotal': subtotal,
                        'tax': tax_total,
                        'total': total
                    }
                    
                    # Save invoice data
                    if save_invoice(invoice_data):
                        st.success(f"Invoice {invoice_id} generated successfully!")
                        
                        # Store current invoice in session state
                        st.session_state.current_invoice = {
                            'invoice_data': invoice_data,
                            'selected_products': st.session_state.selected_products.copy()
                        }
                        
                        # Display invoice
                        st.header(f"Invoice #{invoice_id}")
                        st.subheader("Invoice Details")
                        
                        # Show invoice details in a clean format
                        invoice_col1, invoice_col2 = st.columns(2)
                        
                        with invoice_col1:
                            st.markdown("**Bill To:**")
                            st.markdown(f"{customer_name}")
                            st.markdown(f"{customer_email}")
                            st.markdown(f"{customer_phone}")
                            st.markdown(f"{customer_address}")
                        
                        with invoice_col2:
                            st.markdown(f"**Invoice ID:** {invoice_id}")
                            st.markdown(f"**Date:** {datetime.now().strftime('%Y-%m-%d')}")
                            st.markdown(f"**Total Due:** ₹{total:.2f}")
                        
                        # Generate and display PDF download link
                        pdf_buffer = create_pdf_invoice(invoice_data, st.session_state.selected_products, company_settings)
                        pdf_filename = f"Invoice_{invoice_id}.pdf"
                        st.markdown(get_pdf_download_link(pdf_buffer, pdf_filename), unsafe_allow_html=True)
                        
                        # Reset the form
                        st.session_state.selected_products = []
        else:
            st.info("No products added to invoice yet. Please add products above.")
        
        # View previous invoices section
        st.header("Previous Invoices")
        invoice_df = load_invoice_data()
        
        if not invoice_df.empty:
            invoice_table = st.dataframe(invoice_df[['invoice_id', 'date', 'customer_name', 'total']])
            
            # Provide option to regenerate PDF for previous invoices
            st.subheader("Download Previous Invoice")
            selected_invoice_id = st.selectbox("Select Invoice ID", invoice_df['invoice_id'].tolist())
            
            if st.button("Generate PDF"):
                # Get the invoice data
                selected_invoice = invoice_df[invoice_df['invoice_id'] == selected_invoice_id].iloc[0]
                
                # Parse the stored invoice data
                products_list = eval(selected_invoice['products'])
                quantities_list = eval(selected_invoice['quantities'])
                
                # Check if the invoice has the new format with discount info
                if 'mrps' in selected_invoice and pd.notna(selected_invoice['mrps']):
                    # New format - use stored discount information
                    mrps_list = eval(selected_invoice['mrps'])
                    discount_percentages_list = eval(selected_invoice['discount_percentages'])
                    prices_list = eval(selected_invoice['prices'])
                    
                    selected_products = []
                    for i, (product_name, quantity) in enumerate(zip(products_list, quantities_list)):
                        product_info = product_df[product_df['product_name'] == product_name].iloc[0]
                        tax_rate = float(product_info['product_tax_rate'])
                        
                        selected_products.append({
                            'product_id': product_info['product_id'],
                            'product_name': product_name,
                            'mrp': mrps_list[i],
                            'discount_percentage': discount_percentages_list[i],
                            'price': prices_list[i],
                            'quantity': quantity,
                            'tax_rate': tax_rate,
                            'tax_amount': prices_list[i] * quantity * tax_rate,
                            'amount': prices_list[i] * quantity
                        })
                else:
                    # Old format - use default discounts (for backward compatibility)
                    selected_products = []
                    for product_name, quantity in zip(products_list, quantities_list):
                        product_info = product_df[product_df['product_name'] == product_name].iloc[0]
                        mrp = float(product_info['product_mrp'])
                        default_discount = float(product_info['product_default_discount'])
                        price = calculate_price(mrp, default_discount)
                        tax_rate = float(product_info['product_tax_rate'])
                        selected_products.append({
                            'product_id': product_info['product_id'],
                            'product_name': product_name,
                            'mrp': mrp,
                            'discount_percentage': default_discount,
                            'price': price,
                            'quantity': quantity,
                            'tax_rate': tax_rate,
                            'tax_amount': price * quantity * tax_rate,
                            'amount': price * quantity
                        })
                
                # Create PDF
                pdf_buffer = create_pdf_invoice(selected_invoice, selected_products, company_settings)
                pdf_filename = f"Invoice_{selected_invoice_id}.pdf"
                st.markdown(get_pdf_download_link(pdf_buffer, pdf_filename), unsafe_allow_html=True)
        else:
            st.info("No previous invoices found.")
    
    # Company Settings Tab
    with tab2:
        st.header("Company Settings")
        
        st.subheader("Company Information")
        company_name = st.text_input("Company Name", value=company_settings['company_name'])
        company_address = st.text_area("Company Address", value=company_settings['company_address'])
        company_phone = st.text_input("Company Phone", value=company_settings['company_phone'])
        company_email = st.text_input("Company Email", value=company_settings['company_email'])
        company_website = st.text_input("Company Website", value=company_settings['company_website'])
        
        st.subheader("Company Logo")
        # Display current logo if exists
        if company_settings['company_logo_path'] and os.path.exists(company_settings['company_logo_path']):
            st.image(company_settings['company_logo_path'], width=200)
        
        # Logo upload
        uploaded_logo = st.file_uploader("Upload Company Logo", type=['png', 'jpg', 'jpeg'])
        if uploaded_logo is not None:
            # Save the uploaded logo to a file
            logo_path = f"company_logo.{uploaded_logo.name.split('.')[-1]}"
            with open(logo_path, "wb") as f:
                f.write(uploaded_logo.getbuffer())
            st.success(f"Logo uploaded successfully: {logo_path}")
            
            # Display the uploaded logo
            st.image(logo_path, width=200)
            
            # Update logo path in settings
            company_settings['company_logo_path'] = logo_path
        
        st.subheader("Invoice Settings")
        invoice_terms = st.text_area("Invoice Terms & Conditions", value=company_settings['invoice_terms'])
        
        # Save settings button
        if st.button("Save Company Settings"):
            # Update settings
            company_settings.update({
                "company_name": company_name,
                "company_address": company_address,
                "company_phone": company_phone,
                "company_email": company_email,
                "company_website": company_website,
                "invoice_terms": invoice_terms
            })
            
            # Save to file
            if save_company_settings(company_settings):
                st.success("Company settings saved successfully!")

if __name__ == "__main__":
    main()
