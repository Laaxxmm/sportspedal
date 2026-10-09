"""Shared FPDF base for invoices and challans.

The built-in Helvetica font only covers Latin-1. Phone keyboards insert curly
quotes (D’souza), dashes and the rupee sign, and any of those in a customer
name, address or product made PDF generation raise
FPDFUnicodeEncodingException - a 500 instead of an invoice.
"""
from fpdf import FPDF

_REPLACEMENTS = {
    '‘': "'", '’': "'", '‚': "'", '‛': "'",
    '“': '"', '”': '"', '„': '"',
    '–': '-', '—': '-', '―': '-', '−': '-',
    '…': '...', '₹': 'Rs.', '•': '*',
    ' ': ' ', '​': '', '‌': '', '‍': '',
}


def pdf_safe(text):
    """Map common Unicode punctuation to ASCII, then drop anything outside Latin-1."""
    if text is None:
        return ''
    text = str(text)
    for src, dst in _REPLACEMENTS.items():
        if src in text:
            text = text.replace(src, dst)
    return text.encode('latin-1', 'replace').decode('latin-1')


class SafeFPDF(FPDF):
    def normalize_text(self, text):
        return super().normalize_text(pdf_safe(text))
