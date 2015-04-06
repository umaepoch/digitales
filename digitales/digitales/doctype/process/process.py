# Copyright (c) 2013, digitales and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Process(Document):
	pass

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
		self.check_occurence_of_service()
		self.check_itemis_service_item()


	def check_occurence_of_service
		list1=[]
		for d in self.get('shelf_ready_service_details'):
			if d.process:
				list1.append(d.process)
		frappe.errprint(list1)
		if list1.count(d.process) > 1:
			frappe.throw(" '"+d.process+"' shelf ready serice is added muliple times in child table",raise_exception=1)

		
	def check_itemis_service_item(self):
		for d in self.get('shelf_ready_services_details'):
			if d.process:
				service_item=frappe.db.sql("""select is_Service_item from `tabItem` where name='%s'"""%d.process,as_list=1)
				if service_item:
					if service_item[0][0]=='No':
						frappe.throw(" '"+d.process+"' is not service item.",raise_exception=1)
				
