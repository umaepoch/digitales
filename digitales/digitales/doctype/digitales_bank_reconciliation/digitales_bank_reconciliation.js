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
	// get entries
	// Display POP UP
	if(doc.entries.length == 0)
		msgprint("No journal entries to update")
	else{
		pop_up = render_pop_up_dialog1(doc);
		pop_up.show()

		// make fields read only
		// $("input[data-fieldname$='out_of_balance']").prop("readonly", true);
		// $("input[data-fieldname$='total_debit']").prop("readonly", true);
		// $("input[data-fieldname$='total_credit']").prop("readonly", true);

		// append the journal entries to pop up

		// append_entries(pop_up,doc)
	}
}

render_pop_up_dialog1 = function(doc){
	this.pop_up = new frappe.ui.Dialog({
		title: "Select Items To Reconcile",
		no_submit_on_enter: true,
		fields: [
			{label:__("Digitales Bank Reconciliation"), fieldtype:"HTML", fieldname:"reconcile"},
		],

		primary_action_label: "Reconcile & Submit",
		primary_action: function() {
			msgprint("primary_action")
		}
	});

	append_pop_up_dialog_body(pop_up);
	append_journal_entries(doc);
	return pop_up;
}

append_pop_up_dialog_body = function(){
	this.fd = pop_up.fields_dict;
	// this.pop_up_body = $("<div class='row'><div class='col-xs-4'>Account <input class='input-with-feedback form-control' type='text' name='account' readonly></div><div class='col-xs-4'>From Date <input class='input-with-feedback form-control' type='text' name='from' readonly></div><div class='col-xs-4'>To BS Date <input class='input-with-feedback form-control' type='text' name='to' readonly></div></div><br><div class='row'><div class='col-xs-4'>Out Of Balance <input class='input-with-feedback form-control' type='text' name='out_of_balance' value='0.0' readonly></div><div class='col-xs-4'>Total Debit <input class='input-with-feedback form-control' type='text' name='total_debit' value='0.0' readonly></div><div class='col-xs-4'>Total Credit <input class='input-with-feedback form-control' type='text' name='total_credit' value='0.0' readonly></div></div><br><div class='row'><div class='col-xs-12'><table class='table table-bordered table-hover' id='entries'><thead><th><inputtype='checkbox' id='all' /></th><th><b>Posting Date</b></th><th><b>Voucher ID</b></th><th><b>Clearance Date</b></th><th><b>Against Account</b></th><th><b>Credit</b></th><th><b>Debit</b></th></thead><tbody></tbody></table></div></div>").appendTo($(this.fd.reconcile.wrapper));
	this.pop_up_body = $("<div class='row'><div class='col-xs-3'>From <input class='input-with-feedback form-control' type='text' name='from' readonly></div><div class='col-xs-3'>To <input class='input-with-feedback form-control' type='text' name='to' readonly></div><div class='col-xs-3'>Account <input class='input-with-feedback form-control' type='text' name='account' readonly></div><div class='col-xs-3'>BS Balance <input class='input-with-feedback form-control' type='text' name='bs_balance' readonly></div></div><br><div class='row'><div class='col-xs-3'>Opening Balance <input class='input-with-feedback form-control' type='text' name='opening_balance' readonly></div><div class='col-xs-3'>Out Of Balance <input class='input-with-feedback form-control' type='text' name='out_of_balance' value='0.0' readonly></div><div class='col-xs-3'>Total Debit <input class='input-with-feedback form-control' type='text' name='total_debit' value='0.0' readonly></div><div class='col-xs-3'>Total Credit <input class='input-with-feedback form-control' type='text' name='total_credit' value='0.0' readonly></div></div><br><div class='row'><div class='col-xs-12'><table class='table table-bordered table-hover' id='entries'><thead><th><inputtype='checkbox' id='all' /></th><th><b>Posting Date</b></th><th><b>Voucher ID</b></th><th><b>Clearance Date</b></th><th><b>Against Account</b></th><th><b>Credit</b></th><th><b>Debit</b></th></thead><tbody></tbody></table></div></div>").appendTo($(this.fd.reconcile.wrapper));
}

append_journal_entries = function(doc){
	// appending from, to, account information, BS balance, opening_balance
	$("[name='from']").val(doc.from_date)
	$("[name='to']").val(doc.to_date)
	$("[name='account']").val(doc.bank_account)
	$("[name='bs_balance']").val(0.0)
	$("[name='opening_balance']").val(doc.opening_balance)
	// appending journal voucher entries
	var je = doc.entries
	for (var i = je.length - 1; i >= 0; i--) {
		$("<tr><td><input type='checkbox' class='select'></td>\
			<td align='center'>"+ je[i].posting_date +"</td>\
			<td align='center'>"+ je[i].voucher_id +"</td>\
			<td align='center'>"+ (typeof(je[i].clearance_date) == "undefined"? "Not Set": je[i].clearance_date) +"</td>\
			<td align='center'>"+ je[i].against_account +"</td>\
			<td align='center'>"+ (typeof(je[i].credit) == "undefined"? 0.0: je[i].credit) +"</td>\
			<td align='center'>"+ (typeof(je[i].debit) == "undefined"? 0.0: je[i].debit) +"</td></tr>").appendTo($("#entries tbody"));
	};
}

// render_pop_up_dialog = function(doc){
// 	return new frappe.ui.Dialog({
// 		title: "Select Items To Reconcile",
// 		no_submit_on_enter: true,
// 		fields: [
// 			{label:__("Out Of Balance"), fieldtype:"Float", fieldname:"out_of_balance"},
// 			// {fieldtype: "Column Break"},
// 			{label:__("Total Debit"), fieldtype:"Float", fieldname:"total_debit"},
// 			// {fieldtype: "Column Break"},
// 			{label:__("Total Credit"), fieldtype:"Float", fieldname:"total_credit"},
// 			// {label:__("Journal Entries"), fieldtype: "Section Break", fieldname:"sb"},
// 			{label:__("Entries"), fieldtype:"HTML", fieldname:"entries"},
// 		],
//
// 		primary_action_label: "Reconcile & Submit",
//
// 		primary_action: function() {
// 			// to = $("input[data-fieldname$='recipients']").val().split(",");
// 			// msg = $("textarea[data-fieldname$='content']").val();
//
// 			// return frappe.call({
// 			// 	method: "erpnext.setup.doctype.sms_settings.sms_settings.send_sms",
// 			// 	args: {
// 			// 		receiver_list: to,
// 			// 		msg: msg
// 			// 	},
// 			// 	callback: function(r) {
// 			// 		_me.dialog.hide();
// 			// 		if (email_dialog){
// 			// 			console.log(me)
// 			// 			new frappe.views.CommunicationComposer({
// 			// 				doc: me.frm.doc,
// 			// 				txt: frappe.markdown(me.input.val()),
// 			// 				frm: me.frm
// 			// 			})
// 			// 			recipients = me.frm.doc.raised_by? me.frm.doc.raised_by : me.frm.doc.contact_email? me.frm.doc.contact_email : "";
// 			// 			$("input[data-fieldname='recipients']").val(recipients);
// 			// 			$(".frappe-list").val(msg);
// 			// 		}
// 			// 		if(r.exc) {
// 			// 			msgprint(r.exc);
// 			// 			return;
// 			// 		}
// 			// 	}
// 			// });
// 		}
// 	});
// }

append_entries = function(pop_up, doc){
	this.fd = pop_up.fields_dict;

	this.journal_entries = $("<div class='row'><div class='col-xs-12'><table class='table table-bordered table-hover' id='entries'>\
		<thead><th><input type='checkbox' id='all' /></th><th><b>Posting Date</b></th><th><b>Voucher ID</b></th>\
		<th><b>Clearance Date</b></th><th><b>Against Account</b></th><th><b>Credit</b></th><th><b>Debit</b></th>\
		</thead><tbody></tbody></table></div></div>").appendTo($(this.fd.entries.wrapper));
	// console.log(fd.entries);
	// appending the journal entries to table
	var je = doc.entries
	for (var i = je.length - 1; i >= 0; i--) {
		$("<tr><td><input type='checkbox' class='select'></td>\
			<td align='center'>"+ je[i].posting_date +"</td>\
			<td align='center'>"+ je[i].voucher_id +"</td>\
			<td align='center'>"+ je[i].clearance_date +"</td>\
			<td align='center'>"+ je[i].against_account +"</td>\
			<td align='center'>"+ je[i].credit +"</td>\
			<td align='center'>"+ je[i].debit +"</td></tr>").appendTo($("#entries tbody"));
	};
}
