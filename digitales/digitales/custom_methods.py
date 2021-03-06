
from __future__ import unicode_literals
import frappe
import requests
from requests_oauthlib import OAuth1 as OAuth
from frappe.widgets.reportview import get_match_cond
from frappe import _, msgprint, throw
from frappe.utils import get_url_to_form, add_days, cint, cstr, date_diff, rounded, flt, getdate, nowdate, \
	get_first_day, get_last_day,money_in_words, now, nowtime
#from frappe.utils import add_days, cint, cstr, flt, getdate, nowdate, rounded
from frappe import _
from frappe.utils import cstr

def send_mail_SchedulerLog(doc, method):
	pass

def delivery_note(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql(''' select name from `tabDelivery Note`
		where docstatus <> 2 and name like "%%%s%%" limit %s, %s'''%(txt, start, page_len), as_list = 1)
	
def approve_attendance(doc, method):
	user = frappe.session.user

	if doc.attendance_approver and user != doc.attendance_approver:
		frappe.throw(_("Only '{0}' can approve this Attendance.").format(doc.attendance_approver))

	if (doc.attendance_approver and user == doc.attendance_approver and doc.send_mail_to_approver ==1) or not doc.attendance_approver:
		frappe.db.set_value(doc.doctype, doc.name, "approval_status", "Approved")
		frappe.msgprint("Attendance Approved Successfully")
	else:
		frappe.throw(_("This attendance is not sent for approval yet."))
		# att_details = {"approver": doc.attendance_approver, "date": doc.att_date,
		# 		"path": get_url_to_form(doc.doctype, doc.name), "status": "approved"}
		# template = "templates/emails/attendance_notification.html"

		# subject = "Attendance approved for date {0}.".format(doc.att_date)
		# recipients = frappe.db.get_value("Employee", doc.employee, "user_id")
		# message = frappe.get_template(template).render({"att_details": att_details})
		#frappe.sendmail(recipients=recipients, subject=subject,message= message)

@frappe.whitelist()
def send_mail_to_approver(doctype,doc_name,att_date,employee_name,attendance_approver):
	attendance_doc = frappe.get_doc("Attendance",doc_name)
	attendance_doc.send_mail_to_approver = 1
	attendance_doc.save(ignore_permissions=True)
	att_details = {"employee": employee_name, "date": att_date,
				"path": get_url_to_form(doctype, doc_name), "status": "pending"}
	template = "templates/emails/attendance_notification.html"

	subject = "Pending Attendance Approval of {0} for date {1}.".format(employee_name,att_date)
	recipients = frappe.db.get_value("User",attendance_approver, "email")
	message = frappe.get_template(template).render({"att_details": att_details})
	try:
		frappe.sendmail(recipients=recipients, subject=subject,message= message)
		return "Success"
	except:
		msgprint(_("sendmail Error"), raise_exception=1)

@frappe.whitelist()
def get_attendance_approver(employee):
	return frappe.db.get_value("Employee",{"name":employee},["attendance_approver","employee_name"])

@frappe.whitelist()
def update_po_no(parent, budget, so_name, status):
	po_no = frappe.db.get_value("Budget Details", {'budget':budget, 'parent':parent}, 'po_number')

	if po_no and int(status) == 1:
		frappe.db.set_value("Sales Order", so_name, "po_no", po_no)
		frappe.db.set_value("Sales Order", so_name, "budget", budget)

		return "Reload"

	if po_no and int(status) == 0:
		return po_no

	else:
		return ""

def get_custom_attribute_value (custom_attributes_list,attribute) :
    attribute_value=None
    for custom_attributes in custom_attributes_list:  # travelling each custom_attributes of  item
        if custom_attributes.get("attribute_code") == attribute:
            attribute_value = custom_attributes.get("value")
            return attribute_value
    return attribute_value


@frappe.whitelist()
def url_test_name():
	url=frappe.utils.get_url()
	return url

