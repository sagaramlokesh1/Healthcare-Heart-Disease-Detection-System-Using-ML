@app.route('/generate_report/<int:prediction_id>')
@login_required
def generate_report(prediction_id):
    """Generate a PDF report for a given prediction."""
    if not REPORTLAB_AVAILABLE:
        flash('PDF generation requires ReportLab. Install with: pip install reportlab', 'error')
        return redirect(url_for('report_preview', prediction_id=prediction_id))

    pred = predictions_db.get(prediction_id)
    if not pred:
        flash('Report not found', 'error')
        return redirect(url_for('reports'))

    patient_id = pred['patient_id']
    patient = patients_db.get(patient_id, {})
    if not patient:
        patient = {'name': 'Unknown', 'age': 'N/A', 'gender': 'N/A', 'phone': 'N/A',
                   'email': 'N/A', 'medical_history': 'None'}

    # Create PDF buffer
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=72)
    styles = getSampleStyleSheet()
    story = []

    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#0056b3'),
        alignment=TA_CENTER,
        spaceAfter=30
    )
    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=12
    )
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=10,
        leading=14
    )

    # Title
    story.append(Paragraph("MedPredict Clinical Report", title_style))
    story.append(Spacer(1, 0.2 * inch))

    # Report metadata
    meta_data = [
        ["Report ID:", str(pred['id'])],
        ["Date Generated:", datetime.now().strftime('%Y-%m-%d %H:%M')],
        ["Prediction Date:", pred['date']]
    ]
    meta_table = Table(meta_data, colWidths=[1.5 * inch, 3 * inch])
    meta_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (0,-1), colors.lightgrey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.3 * inch))

    # Patient information
    story.append(Paragraph("Patient Information", heading_style))
    patient_data = [
        ["Full Name:", patient.get('name', 'N/A')],
        ["Patient ID:", str(patient.get('id', 'N/A'))],
        ["Age:", str(patient.get('age', 'N/A'))],
        ["Gender:", patient.get('gender', 'N/A').capitalize()],
        ["Phone:", patient.get('phone', 'N/A')],
        ["Email:", patient.get('email', 'N/A')],
        ["Medical History:", patient.get('medical_history', 'None')],
    ]
    patient_table = Table(patient_data, colWidths=[1.5 * inch, 4 * inch])
    patient_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('BACKGROUND', (0,0), (0,-1), colors.lightblue),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(patient_table)
    story.append(Spacer(1, 0.3 * inch))

    # Prediction results
    story.append(Paragraph("Prediction Results", heading_style))
    pred_data = [
        ["Risk Level:", f"<b>{pred['risk_level']}</b>"],
        ["Probability:", f"{pred['probability']}%"],
        ["Recommendation:", pred['recommendation']],
    ]
    # Include clinical scores if present in the prediction dict
    if 'framingham' in pred and pred['framingham']:
        pred_data.append(["Framingham Score:", f"{pred['framingham']:.1f}%"])
    if 'ascvd' in pred and pred['ascvd']:
        pred_data.append(["ASCVD Score:", f"{pred['ascvd']:.1f}%"])
    if 'qrisk3' in pred and pred['qrisk3']:
        pred_data.append(["QRISK3 Score:", f"{pred['qrisk3']:.1f}%"])

    pred_table = Table(pred_data, colWidths=[1.5 * inch, 4 * inch])
    pred_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('BACKGROUND', (0,0), (0,-1), colors.lightyellow),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(pred_table)
    story.append(Spacer(1, 0.3 * inch))

    # Clinical insights (custom based on risk)
    story.append(Paragraph("Clinical Insights", heading_style))
    insights = []
    if patient.get('age', 0) > 60:
        insights.append("• Patient age indicates elevated cardiovascular risk.")
    if pred['risk_level'] == 'High':
        insights.append("• High risk detected – cardiology consultation strongly advised.")
        insights.append("• Immediate lifestyle modifications recommended.")
    elif pred['risk_level'] == 'Medium':
        insights.append("• Moderate risk – consider risk factor management.")
        insights.append("• Follow-up in 3 months.")
    else:
        insights.append("• Low risk – maintain healthy habits.")
    if 'Hypertension' in patient.get('medical_history', ''):
        insights.append("• Hypertension present – ensure BP control (<130/80).")
    if 'Diabetes' in patient.get('medical_history', ''):
        insights.append("• Diabetes management is critical – target HbA1c <7%.")
    for line in insights:
        story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.2 * inch))

    # Disclaimer
    story.append(Paragraph("Disclaimer", heading_style))
    disclaimer = ("This report is generated by an AI-based clinical decision support system. "
                  "The predictions are for informational purposes only and do not constitute medical advice. "
                  "Always consult a qualified healthcare professional for diagnosis and treatment decisions.")
    story.append(Paragraph(disclaimer, normal_style))
    story.append(Spacer(1, 0.2 * inch))

    # Footer
    footer_text = f"MedPredict AI System v2.0 | Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    story.append(Paragraph(footer_text, ParagraphStyle(
        'Footer', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, textColor=colors.grey)))

    # Build PDF
    doc.build(story)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"MedPredict_Report_{prediction_id}.pdf",
        mimetype='application/pdf'
    )