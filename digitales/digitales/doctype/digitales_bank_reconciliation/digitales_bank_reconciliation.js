// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.onload = function(doc, cdt, cdn){
	cur_frm.set_intro('<i class="icon-question" /> ' +
		__("Update clearance date of Journal Entries marked as 'Bank Vouchers'"));

	cur_frm.add_fetch("bank_account", "company", "company");

	cur_frm.set_query("bank_account", function() {
		return {
			"filters": {
				"account_type": "Bank",
				// "report_type": "Balance Sheet",
				"group_or_ledger": "Ledger"
			}
		};
	});
}

cur_frm.cscript.update_clearance_date = function(doc, cdt,cdn){
	if(!doc.bank_statement_balance &&  !doc.opening_balance)
		frappe.throw("Bank Statement Balance and Opening Balance is Mandetory");
	if(doc.entries.length == 0)
		msgprint("No journal entries to update")
	else{
		pop_up = new frappe.ReconcileJournalVouchers();
	}
}

cur_frm.cscript.bank_account  = function(doc){
	doc.bank_statement_balance = 0;
	doc.opening_balance = 0;
	doc.out_of_balance = 0
	doc.total_debit = 0;
	doc.total_credit = 0

	cur_frm.refresh_fields();
}

cur_frm.cscript.opening_balance  = function(doc){
	calculate_out_of_balance(doc);
}

cur_frm.cscript.bank_statement_balance = function(doc){
	calculate_out_of_balance(doc);
}

calculate_out_of_balance = function(doc){
	if(doc.is_assets_account)
		doc.out_of_balance = doc.bank_statement_balance - (doc.opening_balance + doc.total_debit - doc.total_credit)
	else
		doc.out_of_balance = doc.bank_statement_balance - (doc.opening_balance - doc.total_debit + doc.total_credit)

	cur_frm.refresh_field("out_of_balance")
}

var jvs_to_reconcile = []

frappe.ReconcileJournalVouchers = Class.extend({
	init: function() {
		this.make();
	},
	make: function() {
		var me = this;
		me.pop_up = this.render_pop_up_dialog(cur_frm.doc,me);

		this.append_pop_up_dialog_body(me.pop_up);
		this.append_journal_entries(cur_frm.doc);

		me.pop_up.show()
	},
	render_pop_up_dialog: function(doc, me){
		return new frappe.ui.Dialog({
			title: "Select Items To Reconcile",
			no_submit_on_enter: true,
			fields: [
				{label:__("Digitales Bank Reconciliation"), fieldtype:"HTML", fieldname:"reconcile"},
			],

			primary_action_label: "Reconcile & Submit",
			primary_action: function() {
				// Update Clearance Date of the checked vouchers
				_me = this;
				if(!jvs_to_reconcile.length)
					msgprint("Please first select the journal entries to reconcile");
				else if(parseFloat($("[name='out_of_balance']").val()) != 0){
					me.pop_up.hide();
					frappe.throw("Invalid Out Of Balance Amount");
				}
				else{
					return cur_frm.call({
						doc: cur_frm.doc,
						args: {
							"jvs":jvs_to_reconcile
						},
						method: "update_details",
						callback: function(r) {
							if(!r.exc) {
								me.pop_up.hide();
								frappe.model.set_default_values(cur_frm.doc);
								// get_server_fields('get_details', '' ,'', cur_frm.doc, cur_frm.doctype, cur_frm.docname, 1);
								msgprint("Clearance Date updated in: "+r.message.join());
								cur_frm.refresh_field("entries");
							}
						}
					});
				}
			}
		});
	},
	append_pop_up_dialog_body: function(pop_up){
		this.fd = pop_up.fields_dict;
		this.pop_up_body = $("<div class='row'><div class='col-xs-3'>From <input class='input-with-feedback form-control' type='text' name='from' readonly></div>\
		<div class='col-xs-3'>To <input class='input-with-feedback form-control' type='text' name='to' readonly></div>\
		<div class='col-xs-3'>Account <input class='input-with-feedback form-control' type='text' name='account' readonly></div>\
		<div class='col-xs-3'>BS Balance <input class='input-with-feedback form-control' type='text' name='bs_balance' readonly></div>\
		</div><br><div class='row'><div class='col-xs-3'>Opening Balance <input class='input-with-feedback form-control' type='text' name='opening_balance' readonly></div>\
		<div class='col-xs-3'>Out Of Balance <input class='input-with-feedback form-control' type='text' name='out_of_balance' value='0.0' readonly></div>\
		<div class='col-xs-3'>Total Debit <input class='input-with-feedback form-control' type='text' name='total_debit' value='0.0' readonly></div>\
		<div class='col-xs-3'>Total Credit <input class='input-with-feedback form-control' type='text' name='total_credit' value='0.0' readonly></div>\
		</div><br><div class='row'><div class='col-xs-12'><table class='table table-bordered table-hover' id='entries'><thead>\
		<th><inputtype='checkbox' id='all' /></th><th><b>Posting Date</b></th><th><b>Voucher ID</b></th><th><b>Clearance Date</b></th>\
		<th><b>Against Account</b></th><th><b>Credit</b></th><th><b>Debit</b></th></thead><tbody></tbody></table></div></div>").appendTo($(this.fd.reconcile.wrapper));
	},
	append_journal_entries: function(doc){
		// appending from, to, account information, BS balance, opening_balance
		$("[name='from']").val(doc.from_date);
		$("[name='to']").val(doc.to_date);
		$("[name='account']").val(doc.bank_account);
		$("[name='bs_balance']").val(parseFloat(doc.bank_statement_balance).toFixed(2));
		$("[name='opening_balance']").val(parseFloat(doc.opening_balance).toFixed(2));
		$("[name='out_of_balance']").val(parseFloat(doc.bank_statement_balance-doc.opening_balance).toFixed(2));
		$("[name='total_debit']").val(0.0);
		$("[name='total_credit']").val(0.0);
		// appending journal voucher entries
		var je = doc.entries;
		for (var i = je.length - 1; i >= 0; i--) {
			$("<tr><td><input type='checkbox' class='select' id='_select'></td>\
				<td align='center'>"+ je[i].posting_date +"</td>\
				<td align='center' id='voucher_id'>"+ je[i].voucher_id +"</td>\
				<td align='center'>"+ (typeof(je[i].clearance_date) == "undefined"? "Not Set": je[i].clearance_date) +"</td>\
				<td align='center'>"+ je[i].against_account +"</td>\
				<td align='center' id='credit'>"+ (typeof(je[i].credit) == "undefined"? 0.0: je[i].credit) +"</td>\
				<td align='center' id='debit'>"+ (typeof(je[i].debit) == "undefined"? 0.0: je[i].debit) +"</td></tr>").appendTo($("#entries tbody"));
		};

		$(this.pop_up_body).find(".select").click(function(){
			row = $(this).parent().parent();

			var total_credit = parseFloat($("[name='total_credit']").val());
			var total_debit = parseFloat($("[name='total_debit']").val());
			var out_of_balance = parseFloat($("[name='out_of_balance']").val());
			var bs_balance = parseFloat($("[name='bs_balance']").val());
			var opening_balance = parseFloat($("[name='opening_balance']").val());
			var credit = parseFloat(row.find("td#credit").html());
			var debit = parseFloat(row.find("td#debit").html());
			// check if check box is checked or Not
			if(row.find('input#_select').is(':checked')){
				total_credit += credit
				total_debit += debit

				// append voucher_id to reconcile
				jvs_to_reconcile.push(row.find("td#voucher_id").html())
			}
			else{
				total_credit -= credit
				total_debit -= debit

				// remove the voucher_id from list
				jvs_to_reconcile.pop(row.find("td#voucher_id").html())
			}

			if(doc.is_assets_account)
				out_of_balance = bs_balance - (opening_balance + total_debit - total_credit);	//for assets
			else
				out_of_balance += (bs_balance - (opening_balance - total_debit + total_credit));	//for liability
			// Set values to pop-up box
			$("[name='total_credit']").val((parseFloat(total_credit).toFixed(2)));
			$("[name='total_debit']").val((parseFloat(total_debit).toFixed(2)));
			$("[name='out_of_balance']").val((parseFloat(out_of_balance).toFixed(2)))
			// set values to form
			doc.out_of_balance = parseFloat(out_of_balance).toFixed(2);
			doc.total_debit = parseFloat(total_debit).toFixed(2);
			doc.total_credit = parseFloat(total_credit).toFixed(2);
			doc.total_amount = flt(total_debit) - flt(total_credit);

			cur_frm.refresh_fields(["total_debit","total_credit","out_of_balance","total_amount"]);
		});
	}
})
