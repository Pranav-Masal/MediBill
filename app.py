import os
import re
from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
import pytesseract
from PIL import Image
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import Table
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret123'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bills.db'

db = SQLAlchemy(app)

if not os.path.exists('uploads'):
    os.makedirs('uploads')

# ================= DATABASE MODEL =================

class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100))
    date = db.Column(db.String(50))
    total_amount = db.Column(db.String(50))


# ================= HOME (UPLOAD) =================

@app.route('/', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['bill']

        if file:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            # OCR
            text = pytesseract.image_to_string(Image.open(filepath))

            # Extract data using regex
            # Extract data using regex
            name = re.search(r'Patient Name[:\-]?\s*(.*)', text, re.IGNORECASE)
            date = re.search(r'Date[:\-]?\s*(.*)', text, re.IGNORECASE)
            total = re.search(r'(Total Amount|Grand Total|TOTAL)[^\d]*([\d,.]+)', text, re.IGNORECASE)

            patient_name = name.group(1).strip() if name else "Not Found"
            bill_date = date.group(1).strip() if date else "Not Found"
            total_amount = total.group(2).strip() if total else "Not Found"



            return render_template('preview.html',
                                   patient_name=patient_name,
                                   date=bill_date,
                                   total_amount=total_amount)

    return render_template('upload.html')


# ================= SAVE BILL =================

@app.route('/save', methods=['POST'])
def save():
    patient_name = request.form['patient_name']
    date = request.form['date']
    total_amount = request.form['total_amount']

    new_bill = Bill(
        patient_name=patient_name,
        date=date,
        total_amount=total_amount
    )

    db.session.add(new_bill)
    db.session.commit()

    return redirect(url_for('generate_pdf', bill_id=new_bill.id))


# ================= GENERATE PDF =================

@app.route('/generate_pdf/<int:bill_id>')
def generate_pdf(bill_id):
    bill = Bill.query.get_or_404(bill_id)

    filename = f"bill_{bill_id}.pdf"
    filepath = os.path.join('uploads', filename)

    doc = SimpleDocTemplate(filepath, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("<b>Medical Bill</b>", styles['Title']))
    elements.append(Spacer(1, 0.5 * inch))

    data = [
        ["Patient Name:", bill.patient_name],
        ["Date:", bill.date],
        ["Total Amount:", bill.total_amount]
    ]

    table = Table(data)
    elements.append(table)

    doc.build(elements)

    return send_file(filepath, as_attachment=True)


# ================= RUN =================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
