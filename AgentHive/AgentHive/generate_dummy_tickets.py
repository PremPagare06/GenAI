"""
Generate dummy ServiceNow ticket PDFs for testing the AI agent
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from datetime import datetime, timedelta
import random
import os

# Sample ticket data with common IT issues and their resolutions
TICKET_TEMPLATES = [
    {
        "category": "Network",
        "issue": "Unable to connect to VPN",
        "description": "User reports unable to connect to corporate VPN from home. Error message: 'Connection timeout'.",
        "resolution": "Reset VPN credentials in Active Directory. Instructed user to download latest VPN client version 5.2.1. Verified firewall rules allow VPN traffic on port 443. Issue resolved after client update and credential reset."
    },
    {
        "category": "Email",
        "issue": "Outlook not syncing emails",
        "description": "User's Outlook client stopped syncing emails since yesterday. Emails visible in webmail but not in desktop client.",
        "resolution": "Cleared Outlook cache and OST file. Recreated Outlook profile. Verified Exchange server connectivity. Emails syncing normally after profile recreation."
    },
    {
        "category": "Hardware",
        "issue": "Laptop overheating and shutting down",
        "description": "User's laptop (Dell Latitude 5520) overheating during normal use and shutting down unexpectedly.",
        "resolution": "Cleaned laptop vents and fans. Updated BIOS to version A15. Replaced thermal paste on CPU. Recommended using laptop cooling pad. Temperature now within normal range."
    },
    {
        "category": "Software",
        "issue": "Microsoft Teams crashing on startup",
        "description": "Teams application crashes immediately after launch. Error code: 0x80004005.",
        "resolution": "Cleared Teams cache from %appdata%\\Microsoft\\Teams. Uninstalled and reinstalled Teams using latest version. Disabled GPU hardware acceleration in Teams settings. Application now stable."
    },
    {
        "category": "Access",
        "issue": "Cannot access shared drive",
        "description": "User unable to access department shared drive (\\\\fileserver\\dept\\marketing). Receives 'Access Denied' error.",
        "resolution": "Verified user's Active Directory group membership. Added user to 'Marketing_ReadWrite' security group. Ran 'gpupdate /force' to refresh group policy. Access granted successfully."
    },
    {
        "category": "Printer",
        "issue": "Printer not responding",
        "description": "Network printer (HP LaserJet Pro M404dn) not responding to print jobs. Jobs stuck in queue.",
        "resolution": "Restarted print spooler service on print server. Cleared print queue. Updated printer firmware to version 20230915. Reset printer network settings. Printer functioning normally."
    },
    {
        "category": "Password",
        "issue": "Account locked due to multiple failed login attempts",
        "description": "User account locked after 5 failed login attempts. User forgot password.",
        "resolution": "Verified user identity through security questions. Unlocked account in Active Directory. Reset password following company policy. Enabled MFA for enhanced security. User able to login successfully."
    },
    {
        "category": "Application",
        "issue": "SAP application error on transaction",
        "description": "User receiving error 'RFC destination not maintained' when running transaction ME21N in SAP.",
        "resolution": "Checked RFC connections in SM59. Recreated RFC destination for backend system. Tested connection successfully. Cleared SAP GUI cache. Transaction now working properly."
    },
    {
        "category": "Performance",
        "issue": "Computer running extremely slow",
        "description": "User's workstation (Windows 10) running very slow. Takes 10+ minutes to boot. Applications freezing frequently.",
        "resolution": "Ran disk cleanup and defragmentation. Disabled unnecessary startup programs. Removed malware using Windows Defender full scan. Upgraded RAM from 8GB to 16GB. System performance significantly improved."
    },
    {
        "category": "Database",
        "issue": "SQL Server connection timeout",
        "description": "Application unable to connect to SQL Server database. Error: 'Connection timeout expired'.",
        "resolution": "Verified SQL Server service running. Checked firewall rules for port 1433. Increased connection timeout in application config from 30 to 60 seconds. Optimized slow-running queries. Connection stable now."
    },
    {
        "category": "Network",
        "issue": "Intermittent network connectivity",
        "description": "User experiencing intermittent network drops every 15-20 minutes. Affects both wired and wireless connections.",
        "resolution": "Replaced faulty network cable. Updated network adapter drivers to latest version. Changed wireless channel to avoid interference. Disabled power management for network adapter. Connectivity now stable."
    },
    {
        "category": "Email",
        "issue": "Unable to send emails with attachments",
        "description": "User can send regular emails but emails with attachments fail. Attachment size is 8MB.",
        "resolution": "Increased mailbox send limit from 5MB to 25MB in Exchange. Configured Outlook to compress large attachments. Verified SMTP relay settings. User can now send attachments up to 25MB."
    },
    {
        "category": "Software",
        "issue": "Adobe Acrobat PDF printing issues",
        "description": "PDFs printing with garbled text and missing images from Adobe Acrobat.",
        "resolution": "Updated Adobe Acrobat to latest version 2023.006.20360. Reset Acrobat preferences. Changed print setting to 'Print as Image'. Updated printer PostScript driver. PDFs printing correctly now."
    },
    {
        "category": "Access",
        "issue": "Multi-factor authentication not working",
        "description": "User not receiving MFA codes via SMS or authenticator app for Office 365 login.",
        "resolution": "Re-registered user's phone number in Azure AD. Reset MFA settings. Configured Microsoft Authenticator app with new QR code. Tested MFA with backup codes. MFA working properly."
    },
    {
        "category": "Hardware",
        "issue": "External monitor not detected",
        "description": "User's external monitor not detected when connected via HDMI to laptop docking station.",
        "resolution": "Updated Intel graphics driver to version 30.0.101.1404. Tested different HDMI cable. Updated docking station firmware. Configured display settings to extend desktop. Monitor detected and working."
    }
]

def generate_ticket_pdf(ticket_data, filename):
    """Generate a single ticket PDF"""
    doc = SimpleDocTemplate(filename, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#003366'),
        spaceAfter=30,
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#0066cc'),
        spaceAfter=10,
    )
    
    # Title
    title = Paragraph("ServiceNow Incident Ticket", title_style)
    story.append(title)
    story.append(Spacer(1, 0.2*inch))
    
    # Ticket metadata table
    metadata = [
        ['Ticket Number:', ticket_data['ticket_number']],
        ['Priority:', ticket_data['priority']],
        ['Status:', ticket_data['status']],
        ['Category:', ticket_data['category']],
        ['Created Date:', ticket_data['created_date']],
        ['Resolved Date:', ticket_data['resolved_date']],
        ['Assigned To:', ticket_data['assigned_to']],
        ['Requester:', ticket_data['requester']],
    ]
    
    t = Table(metadata, colWidths=[2*inch, 4*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e6f2ff')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    
    story.append(t)
    story.append(Spacer(1, 0.3*inch))
    
    # Issue description
    story.append(Paragraph("Issue Summary", heading_style))
    story.append(Paragraph(ticket_data['issue'], styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph("Detailed Description", heading_style))
    story.append(Paragraph(ticket_data['description'], styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Resolution
    story.append(Paragraph("Resolution", heading_style))
    story.append(Paragraph(ticket_data['resolution'], styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Build PDF
    doc.build(story)
    print(f"Generated: {filename}")

def generate_all_tickets(num_tickets=15, output_dir="past_tickets"):
    """Generate multiple dummy ticket PDFs"""
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    priorities = ['P1 - Critical', 'P2 - High', 'P3 - Medium', 'P4 - Low']
    statuses = ['Resolved', 'Closed']
    agents = ['John Smith', 'Sarah Johnson', 'Mike Chen', 'Emily Davis', 'Robert Wilson']
    requesters = ['alice.brown@company.com', 'bob.jones@company.com', 'carol.white@company.com', 
                  'david.lee@company.com', 'emma.taylor@company.com']
    
    base_date = datetime.now() - timedelta(days=180)  # Start 6 months ago
    
    for i in range(num_tickets):
        # Select a template (cycle through them)
        template = TICKET_TEMPLATES[i % len(TICKET_TEMPLATES)]
        
        # Generate dates
        created_date = base_date + timedelta(days=random.randint(0, 150))
        resolved_date = created_date + timedelta(hours=random.randint(2, 72))
        
        ticket_data = {
            'ticket_number': f'INC{1000 + i:04d}',
            'priority': random.choice(priorities),
            'status': random.choice(statuses),
            'category': template['category'],
            'created_date': created_date.strftime('%Y-%m-%d %H:%M:%S'),
            'resolved_date': resolved_date.strftime('%Y-%m-%d %H:%M:%S'),
            'assigned_to': random.choice(agents),
            'requester': random.choice(requesters),
            'issue': template['issue'],
            'description': template['description'],
            'resolution': template['resolution']
        }
        
        filename = os.path.join(output_dir, f"ticket_{ticket_data['ticket_number']}.pdf")
        generate_ticket_pdf(ticket_data, filename)
    
    print(f"\nSuccessfully generated {num_tickets} ticket PDFs in '{output_dir}' directory")

if __name__ == "__main__":
    generate_all_tickets(num_tickets=15)

