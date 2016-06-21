
from __future__ import unicode_literals
import frappe
from frappe.widgets.reportview import get_match_cond
from frappe.utils import add_days, cint, cstr, date_diff, rounded, flt, getdate, nowdate, \
	get_first_day, get_last_day,money_in_words, now, nowtime
#from frappe.utils import add_days, cint, cstr, flt, getdate, nowdate, rounded
from frappe import _

def send_mail_SchedulerLog(doc, method):
	pass

def delivery_note(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql(''' select name from `tabDelivery Note`
		where docstatus <> 2 and name like "%%%s%%" limit %s, %s'''%(txt, start, page_len), as_list = 1)

# def attendance_workflow(doc, method):
# 	user = frappe.session.user
# 	if doc.workflow_state == "Approved" and user != doc.attendance_approver:
# 		frappe.throw(_("Only {0} can Approved this").format(doc.attendance_approver))
# 	elif doc.workflow_state == "Approved" and user == doc.attendance_approver:
# 		doc.workflow_state = "Approved By Manager"
# 		doc.docstatus = 1
		
# def cancel_attendance(doc,method):
# 	doc.workflow_state = "Cancelled"
# 	doc.docstatus = 2