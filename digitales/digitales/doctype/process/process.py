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
			frappe.msgprint("Specified barcode='"+barcode+"' is not present")

	# Update Sales Order Process Status which we required in sales invoice generation fron sales order---------------------------------------
	def on_submit(self):
		frappe.db.sql("""update `tabSales Order` set process_status='Uncompleted' 
							where name='%s'"""%self.get_sales_order)
		frappe.db.commit()

