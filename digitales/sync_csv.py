import frappe
import csv

def write_csv():
	so = frappe.get_doc('Sales Order', 'SO-02263')
	so.submit()		