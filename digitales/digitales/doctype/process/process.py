# Copyright (c) 2013, digitales and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class Process(Document):
	def validate(self):
		self.validate_SO_DN()

	def validate_SO_DN(self):
		if self.get_sales_order and self.get_delivery_note:
			frappe.throw(_("Select 'Get Sales Order' OR 'Get Delivery Note'"))
		if not self.get_sales_order and not self.get_delivery_note:
			frappe.throw(_("Select either 'Get Sales Order' OR 'Get Delivery Note'"))

	# To fetch Shelf Ready Service Details against the specified barcode--------------------------------------------------
	def get_service_details(self,barcode):
		item_details= frappe.db.sql("""select name,charge
										from `tabShelf Ready Service` 
											where barcode='%s'"""%barcode)
		#frappe.errprint(item_details[0][0])
		if item_details:
			ret={
				"process":item_details[0][0],
				"charge":item_details[0][1]	
				#"file_name":item_details[0][2],
				#"file_attachment":item_details[0][3]
			}
			return ret

		else:
			frappe.msgprint("Specified barcode is not valid barcode")

	# Update Sales Order Process Status which we required in sales invoice generation fron sales order---------------------------------------
	def on_submit(self):
		frappe.db.sql("""update `tabSales Order` set process_status='Uncompleted' 
							where name='%s'"""%self.get_sales_order)
		frappe.db.commit()


	def on_update(self):
		#frappe.errprint("in on update")
		# self.check_occurence_of_service()
		self.check_itemis_service_item()

	def check_occurence_of_service(self):
		list1=[]
		for d in self.get('shelf_ready_service_details'):
			if d.process:
				list1.append(d.process)
		#frappe.errprint(list1)
		if list1.count(d.process) > 1:
			frappe.throw(" '"+d.process+"' shelf ready serice is added muliple times in child table")

		
	def check_itemis_service_item(self):
		for d in self.get('shelf_ready_service_details'):
			if d.process:
				service_item=frappe.db.sql("""select is_Service_item from `tabItem` where name='%s'"""%d.process,as_list=1)
				if service_item:
					if service_item[0][0]=='No':
						frappe.throw(" '"+d.process+"' is not service item.")

@frappe.whitelist()
def get_process_from_barcode(barcode):
	"""
		return the process name from barcode
	"""
	return frappe.db.get_value('Item', {'barcode': barcode}, 'name')

def get_shelfreadyservices_customer(doctype, txt, searchfield, start, page_len, filters):
	query = """select name1 from `tabShelf Ready Services` where parent='%(parent)s' and name1 like "%(txt)s" limit %(start)s, %(page_len)s"""
	query = query%{
				"parent": filters.get('customer_name'),
				"txt": "%%%s%%"%txt,
				"start": start,
				"page_len": page_len
			}

	return frappe.db.sql(query)