import frappe
import csv

def write_csv():
	print "hellooo"
	with open('/home/erpnext/12.csv') as csvfile:
		reader = csv.reader(csvfile)
		for row in reader:
			if frappe.db.get_value("Item",row[0],"name"):
				frappe.db.sql("""update `tabItem` set artist = %s where name=%s""", (row[1],row[0]))
			