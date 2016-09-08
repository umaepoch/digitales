
from __future__ import unicode_literals
import frappe
from frappe.widgets.reportview import get_match_cond
from frappe.utils import get_url_to_form, add_days, cint, cstr, date_diff, rounded, flt, getdate, nowdate, \
	get_first_day, get_last_day,money_in_words, now, nowtime
#from frappe.utils import add_days, cint, cstr, flt, getdate, nowdate, rounded
from frappe import _

def send_mail_SchedulerLog(doc, method):
	pass

def delivery_note(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql(''' select name from `tabDelivery Note`
		where docstatus <> 2 and name like "%%%s%%" limit %s, %s'''%(txt, start, page_len), as_list = 1)

def pending_approval(doc, method):
	doc.approval_status = "Pending approval"
	if not doc.attendance_approver:
		frappe.throw(_("Please set Attendance Approver on Employee form"))
	att_details = {"employee": doc.employee_name, "date": doc.att_date,
				"path": get_url_to_form(doc.doctype, doc.name), "status": "pending"}
	template = "templates/emails/attendance_notification.html"

	subject = "Pending Attendance Approval of {0} for date {1}.".format(doc.employee_name, doc.att_date)
	recipients = frappe.db.get_value("User", doc.attendance_approver, "email")
	message = frappe.get_template(template).render({"att_details": att_details})
	frappe.sendmail(recipients=recipients, subject=subject,message= message)

def approve_attendance(doc, method):
	user = frappe.session.user
	if not doc.attendance_approver:
		frappe.throw(_("Please set Attendance Approver on Employee form"))
	if doc.attendance_approver and user != doc.attendance_approver:
		frappe.throw(_("Only '{0}' can approve this Attendance.").format(doc.attendance_approver))
	else:
		frappe.db.set_value(doc.doctype, doc.name, "approval_status", "Approved")
		att_details = {"approver": doc.attendance_approver, "date": doc.att_date,
				"path": get_url_to_form(doc.doctype, doc.name), "status": "approved"}
		template = "templates/emails/attendance_notification.html"

		subject = "Attendance approved for date {0}.".format(doc.att_date)
		recipients = frappe.db.get_value("Employee", doc.employee, "user_id")
		message = frappe.get_template(template).render({"att_details": att_details})
		frappe.sendmail(recipients=recipients, subject=subject,message= message)

@frappe.whitelist()
def update_po_no(parent, budget, so_name, status):
	po_no = frappe.db.get_value("Budget Details", {'budget':budget, 'parent':parent}, 'po_number')
	if po_no and int(status) == 1:
		frappe.db.set_value("Sales Order", so_name, "po_no", po_no)
		frappe.db.set_value("Sales Order", so_name, "budget", budget)

	if po_no and int(status) == 0:
		return po_no