# Copyright (c) 2013, digitales and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, getdate, nowdate
from frappe import msgprint, _
from frappe.model.document import Document

class DigitalesBankReconciliation(Document):
	def get_details(self):
		if not (self.bank_account and self.from_date and self.to_date):
			msgprint("Bank Account, From Date and To Date are Mandatory")
			return

		condition = ""
		if not self.include_reconciled_entries:
			condition = "and ifnull(clearance_date, '') in ('', '0000-00-00')"


		dl = frappe.db.sql("""select t1.name, t1.cheque_no, t1.cheque_date, t2.debit,
				t2.credit, t1.posting_date, t2.against_account, t1.clearance_date
			from
				`tabJournal Voucher` t1, `tabJournal Voucher Detail` t2
			where
				t2.parent = t1.name and t2.account = %s
				and t1.posting_date >= %s and t1.posting_date <= %s and t1.docstatus=1
				and ifnull(t1.is_opening, 'No') = 'No' %s""" %
				('%s', '%s', '%s', condition), (self.bank_account, self.from_date, self.to_date), as_dict=1)

		self.set('entries', [])
		self.total_amount = 0.0
		self.total_debit = 0.0
		self.total_credit = 0.0
		self.is_assets_account = 1 if frappe.db.get_value("Account",self.bank_account,'root_type') == "Asset" else 0

		for d in dl:
			nl = self.append('entries', {})
			nl.posting_date = d.posting_date
			nl.voucher_id = d.name
			nl.cheque_number = d.cheque_no
			nl.cheque_date = d.cheque_date
			nl.debit = d.debit
			nl.credit = d.credit
			nl.against_account = d.against_account
			nl.clearance_date = d.clearance_date
			self.total_amount += flt(d.debit) - flt(d.credit)
			self.total_debit+=flt(d.debit)
			self.total_credit+=flt(d.credit)

@frappe.whitelist()
def update_details(doc,jvs):
	import json

	vouchers = []
	entries = json.loads(doc)
	for d in entries.get('entries'):
		if d.get('clearance_date') and d.get('voucher_id') in jvs:
			if d.get('cheque_date') and getdate(d.get("clearance_date")) < getdate(d.get('cheque_date')):
				frappe.throw(_("Clearance date cannot be before check date in row {0}").format(d.get('idx')))

			frappe.db.set_value("Journal Voucher", d.get('voucher_id'), "clearance_date", d.get('clearance_date'))
			frappe.db.sql("""update `tabJournal Voucher` set clearance_date = %s, modified = %s
				where name=%s""", (d.get('clearance_date'), nowdate(), d.get('voucher_id')))
			vouchers.append(d.get('voucher_id'))

	return vouchers
	# if vouchers:
	# 	msgprint("Clearance Date updated in: {0}".format(", ".join(vouchers)))
	# else:
	# 	msgprint(_("Clearance Date not mentioned"))
