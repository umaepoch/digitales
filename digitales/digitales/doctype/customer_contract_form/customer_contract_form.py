# Copyright (c) 2013, digitales and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import add_days, cint, cstr, flt, getdate, nowdate, rounded

class CustomerContractForm(Document):
	pass


	def on_update(self):
		contract_name= frappe.db.sql("""select name from `tabCustomer Contract Form` 
										where customer='%s' and docstatus!=2 and name!= '%s'"""
										%(self.customer,self.name),debug=1)
		#frappe.errprint(contract_name)
		if contract_name:
			contract_details=frappe.db.sql("""select contract_start_date,contract_end_date from `tabCustomer Contract Form` 
							where name= '%s'"""%(contract_name[0][0]),debug=1)
			#frappe.errprint(contract_details)
			if contract_details:
				#rappe.errprint(contract_details[0][0] <= getdate(self.contract_start_date) or contract_details[0][1] >= getdate(self.contract_end_date))
				if contract_details[0][1] >= getdate(self.contract_start_date):
					frappe.msgprint("There is already one contract = %s is created aginst the current customer whose contrct start date = %s and contract end date = %s"%(contract_name[0][0],contract_details[0][0],contract_details[0][1]),raise_exception=1)
				else:
					pass

			else:
				pass

		else:
			pass

		