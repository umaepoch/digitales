# Copyright (c) 2013, digitales and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class ShelfReadyService(Document):
	pass

	def validate(self):
		barcode=frappe.db.sql("""select name from `tabShelf Ready Service` where barcode='%s' and name!='%s'
			"""%(self.barcode,self.name),as_list=1)
		#frappe.errprint(barcode)
		if barcode:
			frappe.msgprint("The barcode which you given is already assigned to the Shelf Ready Service='"+barcode[0][0]+"' Please specify another barcode",raise_exception=1)
		else:
			pass
	
