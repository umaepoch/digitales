import frappe
import csv
from frappe.utils import now_datetime, cstr, cint, flt
import json
from datetime import timedelta
import requests
from digitales.Api_methods import GetOauthDetails, get_own_warehouse,\
	media_type, default_ExpenxeIncomeAccount, get_supplier, get_orders_from_magento

oauth_data = GetOauthDetails()
headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
def write_csv():
	pass

def check_lastdate_api():
	try:
		max_item_date = (now_datetime() - timedelta(days = 1)).strftime('%Y-%m-%d %H:%M:%S')
		status = get_SyncCount(max_item_date)
	except Exception, e:
		print e

def get_SyncCount(max_date):
	r = requests.get(url='http://digitales.com.au/api/rest/mcount?start_date='+cstr(max_date)+'', headers=headers, auth=oauth_data)
	total_page_count = json.loads(r.content)
	if total_page_count:
		get_data(total_page_count, max_date)

def get_data(total_page_count, max_date):
	pages = {'a_product(count, max_date)': 'product_pages_per_100_mcount', 'b_customer()': 'customer_pages_per_100_mcount', 'c_order(count, max_date)': 'orders_pages_per_100_mcount'}
	for key, value in pages.items():
		count = total_page_count.get(value)
		if count > 0:
			eval(key)

def a_product(count, max_date):
	for page in range(1, count+1):
		r = requests.get(url='http://digitales.com.au/api/rest/products?filter[1][attribute]=updated_at&filter[1][gt]=%s&page=%s&limit=100&order=updated_at&dir=asc'%(max_date, page), headers=headers, auth=oauth_data)
		product_data = json.loads(r.content)
		for key, value in product_data.items():
			if not frappe.db.get_value('Item', {'event_id': key}, 'name'):
				media = media_type(value.get('media'))
				expense, income = default_ExpenxeIncomeAccount(media)
				supplier = get_supplier(value.get('distributor'))

				product = frappe.get_doc({
					'doctype': 'Item',
					'item_code': value.get('sku'),
					'event_id': key,
					'item_name': value.get('name') or value.get('sku'),
					'description': 'desc %s'%(value.get('short_description')),
					'default_warehouse': get_own_warehouse(),
					'item_group': media,
					'modified_date': value.get('updated_at'),
					'default_supplier': supplier,
					'product_release_date': value.get('release_date'),
                                        'classification': value.get('classification'),
					'expense_account': expense,
					'income_account': income
					})
				product.save(ignore_permissions=True)

				price = frappe.get_doc({
					'doctype': "Item Price",
					'item_code': value.get('sku'),
					'price_list': frappe.db.get_value('Configuration Page', None, 'price_list'),
					'price_list_rate': value.get('price')
					})
				price.save(ignore_permissions=True)

def b_customer():
	pass

def c_order(count, max_date):
	for page in range(1, count+1):
		get_orders_from_magento(page, max_date, headers, oauth_data)
