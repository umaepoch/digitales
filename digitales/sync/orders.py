import frappe
from frappe.utils import cstr
from .utils import log_sync_error
from frappe.utils import add_days, nowdate
import datetime
import time
def create_or_update_sales_order(entity):
	""" create new Sales Order """
	missing_items = []
	missing_customer = None

	try:
		name = frappe.db.get_value("Sales Order", { "entity_id": entity.get("entity_id") })
		customer = frappe.db.get_value('Contact', {'entity_id': entity.get('customer_id')}, 'customer')
		if name:
			# raise Exception("#{} Order updated after sync".format(entity.get("increment_id")))
			return {
				entity.get("entity_id"): {
					"operation": "Order Already Exists",
					"name": name,
					"modified_date": entity.get("updated_at")
				}
			}
		if not entity.get("items"):  #m2_changes
			raise Exception("#{} Order has no Items".format(entity.get("increment_id")))
		if not customer:
			missing_customer = entity.get('customer_id')
			raise Exception("{} customer is not yet syned".format(customer))

		missing_items = get_missing_items(entity.get("items"), entity.get("increment_id"))#m2_changes
		if not missing_items:
			so = frappe.new_doc("Sales Order")
			so.customer = customer
			so.entity_id = entity.get('entity_id')
			so.modified_date = entity.get('updated_at')
			so.delivery_date = add_days(nowdate(), 6)
			so.grand_total_export = entity.get('grand_total')
			so.order_number_details = entity.get('increment_id')
			so.po_no = entity.get('extension_attributes').get('po_number') #m2_changes
			so.magento_budget = entity.get('extension_attributes').get('budget_name')

			# If Order type is general then set SO order type as Standard Order
            		so.new_order_type="Standard Order" #m2_pending order_type not yet known
            #if entity.get('order_type') == "General" or entity.get('order_type') == None:
				#so.new_order_type="Standard Order"
			#else:
				#so.new_order_type = entity.get('order_type')


			so.set('sales_order_details', [])
			for item in entity.get('items'):
				if item and item.get('sku'):
					soi = so.append('sales_order_details', {})
					soi.item_code = item.get("sku")
					soi.release_date_of_item = frappe.db.get("Item", item.get("sku"), "product_release_date") or ""
					soi.qty = item.get('qty_ordered') or 0
					soi.rate = item.get('original_price')
                    			soi.classification = frappe.db.get_value("Item", item.get("sku"), "classification")
                    			soi.poupular = frappe.db.get_value("Item", item.get("sku"), "popular")
					soi.artist = frappe.db.get_value("Item", item.get("sku"), "artist") or "" #m2_pending
                                        #if item.get('special_to_date') is not None and datetime.date.today()<=item.get('special_to_date') : #m2_pending
                                            #if item.get('special_from_date') and datetime.date.today()>=item.get('special_from_date'):
                                                #create_or_update_item_special_price(item) # Add this line and create the function

				# # set shipping and billing address
			#set_sales_order_address(entity, so)
			so.save(ignore_permissions=True)

			return {
				entity.get("entity_id"): {
					"operation": "Order Created" if not name else "Order Updated",
					"name": so.name,
					"modified_date": entity.get("updated_at")
				}
			}
		else:
			raise Exception("({}) items is not yet syned".format(",".join(missing_items)))
	except Exception, e:
		docname = entity.get('entity_id')
		response = entity
		log_sync_error(
			"Sales Order", docname, response,
			e, "create_or_update_sales_order",
			missing_customer=missing_customer,
			missing_items=missing_items
		)

def get_missing_items(items, increment_id):
	""" check if all the items from orders are synced in ERP """
	missing_items = []
	for item in items:
		if item and item.get('sku', None) and not frappe.db.get_value('Item',item.get('sku')):
			error = Exception("%s Item from order #%s is missing or not synced"%(
						item.get('sku'),
						increment_id or ""
					))
			log_sync_error("Item", item.get('sku'), item, error, "get_missing_items")
			missing_items.append(item.get('sku'))

	return missing_items

def set_sales_order_address(address_details, order):
	# sur changed code according to m2.3 structure
	#billing addess
	if(address_details.get("billing_address")):
		address = address_details.get("billing_address")
		addr_filter = { 'entity_id': address.get('customer_address_id') }
		cust_address = frappe.db.get_value('Address', addr_filter)

		if cust_address and address.get('address_type') == "billing":
			order.customer_address = frappe.db.get_value('Address',{ 'entity_id':cust_address })

	#shipping_address
	shipping_assignments = address_details.get("extension_attributes").get("shipping_assignments")
	if shipping_assignments:
	    for shipping_assignment in shipping_assignments:
			shipping_address = shipping_assignment.get("shipping").get("address")
			if (shipping_address.get("address_type") == "shipping"):
			  addr_filter = { 'entity_id': shipping_address.get('customer_address_id') }
			  cust_address = frappe.db.get_value('Address', addr_filter)
			  if cust_address :
				  order.shipping_address_name = frappe.db.get_value('Address', { 'entity_id':cust_address })

def create_or_update_item_special_price(entity):
	# create new Item Price if not available else update
	price = entity.get("price")
	if not price:
		return
	item_price_name = frappe.db.get_value(
						"Item Price",
						{
							"item_code": entity.get("sku"),
							"price_list": "Standard Selling"
						},
						"name"
					)
	if not item_price_name:
		item_price = frappe.new_doc("Item Price")
	else:
		item_price = frappe.get_doc("Item Price", item_price_name)
	item_price.item_code = cstr(entity.get("sku"))
	item_price.price_list = "Standard Selling"
	item_price.price_list_rate = entity.get("special_price", 0)
	item_price.save(ignore_permissions=True)


