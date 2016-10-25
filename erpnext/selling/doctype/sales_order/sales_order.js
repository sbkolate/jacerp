// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

{% include 'erpnext/selling/sales_common.js' %}

frappe.ui.form.on("Sales Order", {
	onload: function(frm) {
		erpnext.queries.setup_queries(frm, "Warehouse", function() {
			return erpnext.queries.warehouse(frm.doc);
		});

		// formatter for material request item
		frm.set_indicator_formatter('item_code',
			function(doc) { return (doc.qty<=doc.delivered_qty) ? "green" : "orange" })
	}
});

erpnext.selling.SalesOrderController = erpnext.selling.SellingController.extend({
	refresh: function(doc, dt, dn) {
		this._super();
		var allow_purchase = false;
		var allow_delivery = false;

		if(doc.docstatus==1) {
			if(doc.status != 'Closed') {

				for (var i in cur_frm.doc.items) {
					var item = cur_frm.doc.items[i];
					if(item.delivered_by_supplier === 1 || item.supplier){
						if(item.qty > flt(item.ordered_qty)
							&& item.qty > flt(item.delivered_qty)) {
							allow_purchase = true;
						}
					}

					if (item.delivered_by_supplier===0) {
						if(item.qty > flt(item.delivered_qty)) {
							allow_delivery = true;
						}
					}

					if (allow_delivery && allow_purchase) {
						break;
					}
				}

				if (this.frm.has_perm("submit")) {
					// close
					if(flt(doc.per_delivered, 2) < 100 || flt(doc.per_billed) < 100) {
							cur_frm.add_custom_button(__('Close'), this.close_sales_order, __("Status"))
						}
				}

				// delivery note
				if(flt(doc.per_delivered, 2) < 100 && ["Sales", "Shopping Cart"].indexOf(doc.order_type)!==-1 && allow_delivery) {
					cur_frm.add_custom_button(__('Delivery'), this.make_delivery_note, __("Make"));
					cur_frm.page.set_inner_btn_group_as_primary(__("Make"));
				}

				// sales invoice
				if(flt(doc.per_billed, 2) < 100) {
					cur_frm.add_custom_button(__('Invoice'), this.make_sales_invoice, __("Make"));
				}

				// material request
				if(!doc.order_type || ["Sales", "Shopping Cart"].indexOf(doc.order_type)!==-1
					&& flt(doc.per_delivered, 2) < 100) {
						cur_frm.add_custom_button(__('Material Request'), this.make_material_request, __("Make"));
				}

				// make purchase order
				if(flt(doc.per_delivered, 2) < 100 && allow_purchase) {
					cur_frm.add_custom_button(__('Purchase Order'), cur_frm.cscript.make_purchase_order, __("Make"));
				}

				if(flt(doc.per_billed)==0) {
					cur_frm.add_custom_button(__('Payment Request'), this.make_payment_request, __("Make"));
					cur_frm.add_custom_button(__('Payment'), cur_frm.cscript.make_payment_entry, __("Make"));
				}

				// maintenance
				if(flt(doc.per_delivered, 2) < 100 &&
						["Sales", "Shopping Cart"].indexOf(doc.order_type)===-1) {
					cur_frm.add_custom_button(__('Maintenance Visit'), this.make_maintenance_visit, __("Make"));
					cur_frm.add_custom_button(__('Maintenance Schedule'), this.make_maintenance_schedule, __("Make"));
				}


			} else {
				if (this.frm.has_perm("submit")) {
					// un-close
					cur_frm.add_custom_button(__('Re-open'), cur_frm.cscript['Unclose Sales Order'], __("Status"));
				}
			}
		}

		if (this.frm.doc.docstatus===0) {
			cur_frm.add_custom_button(__('Quotation'),
				function() {
					erpnext.utils.map_current_doc({
						method: "erpnext.selling.doctype.quotation.quotation.make_sales_order",
						source_doctype: "Quotation",
						get_query_filters: {
							docstatus: 1,
							status: ["!=", "Lost"],
							order_type: cur_frm.doc.order_type,
							customer: cur_frm.doc.customer || undefined,
							company: cur_frm.doc.company
						}
					})
				}, __("Get items from"));
		}

		this.order_type(doc);
	},

	order_type: function() {
		this.frm.toggle_reqd("delivery_date", this.frm.doc.order_type == "Sales");
	},

	tc_name: function() {
		this.get_terms();
	},

	make_material_request: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_material_request",
			frm: cur_frm
		})
	},

	make_delivery_note: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_delivery_note",
			frm: cur_frm
		})
	},

	make_sales_invoice: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice",
			frm: cur_frm
		})
	},

	make_maintenance_schedule: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_maintenance_schedule",
			frm: cur_frm
		})
	},

	make_maintenance_visit: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_maintenance_visit",
			frm: cur_frm
		})
	},

	make_purchase_order: function(){
		var dialog = new frappe.ui.Dialog({
			title: __("For Supplier"),
			fields: [
				{"fieldtype": "Link", "label": __("Supplier"), "fieldname": "supplier", "options":"Supplier",
					"get_query": function () {
						return {
							query:"erpnext.selling.doctype.sales_order.sales_order.get_supplier",
							filters: {'parent': cur_frm.doc.name}
						}
					}, "reqd": 1 },
				{"fieldtype": "Button", "label": __("Make Purchase Order"), "fieldname": "make_purchase_order", "cssClass": "btn-primary"},
			]
		});

		dialog.fields_dict.make_purchase_order.$input.click(function() {
			args = dialog.get_values();
			if(!args) return;
			dialog.hide();
			return frappe.call({
				type: "GET",
				method: "erpnext.selling.doctype.sales_order.sales_order.make_purchase_order_for_drop_shipment",
				args: {
					"source_name": cur_frm.doc.name,
					"for_supplier": args.supplier
				},
				freeze: true,
				callback: function(r) {
					if(!r.exc) {
						var doc = frappe.model.sync(r.message);
						frappe.set_route("Form", r.message.doctype, r.message.name);
					}
				}
			})
		});
		dialog.show();
	},
	close_sales_order: function(){
		cur_frm.cscript.update_status("Close", "Closed")
	}

});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.selling.SalesOrderController({frm: cur_frm}));

cur_frm.cscript.new_contact = function(){
	tn = frappe.model.make_new_doc_and_get_name('Contact');
	locals['Contact'][tn].is_customer = 1;
	if(doc.customer) locals['Contact'][tn].customer = doc.customer;
	frappe.set_route('Form', 'Contact', tn);
}

cur_frm.fields_dict['project'].get_query = function(doc, cdt, cdn) {
	return {
		query: "erpnext.controllers.queries.get_project_name",
		filters: {
			'customer': doc.customer
		}
	}
}

cur_frm.cscript.update_status = function(label, status){
	var doc = cur_frm.doc;
	frappe.ui.form.is_saving = true;
	frappe.call({
		method: "erpnext.selling.doctype.sales_order.sales_order.update_status",
		args: {status: status, name: doc.name},
		callback: function(r){
			cur_frm.reload_doc();
		},
		always: function() {
			frappe.ui.form.is_saving = false;
		}
	});
}

cur_frm.cscript['Unclose Sales Order'] = function() {
	cur_frm.cscript.update_status('Re-open', 'Draft')
}

cur_frm.cscript.on_submit = function(doc, cdt, cdn) {
	if(cint(frappe.boot.notification_settings.sales_order)) {
		cur_frm.email_doc(frappe.boot.notification_settings.sales_order_message);
	}
};

frappe.ui.form.on("Sales Order Item", "rail_sft", function(frm, cdt, cdn) //Created by Amitha M.D.
{
	item = locals[cdt][cdn];
	if(item.deck_sft!=undefined){			
		item = locals[cdt][cdn];   
		var decksft= flt(item.deck_sft);
		var railsft= flt(item.rail_sft);
		total_qty = decksft+railsft;
		item.qty = total_qty;	
		item.total_sft=total_qty;	
		cur_frm.refresh_fields();
	}
	
})

frappe.ui.form.on("Sales Order Item", "deck_sft", function(frm, cdt, cdn) //Created by Amitha M.D.
{
	item = locals[cdt][cdn];
	if(item.rail_sft!=undefined){			
		item = locals[cdt][cdn];   
		var decksft= flt(item.deck_sft);
		var railsft= flt(item.rail_sft);
		total_qty = decksft+railsft;
		item.qty = total_qty;	
		item.total_sft=total_qty;	
		cur_frm.refresh_fields();
	}
	
})

frappe.ui.form.on("Sales Order Item", "custom_amount", function(frm, cdt, cdn) //Created by Amitha M.D.
{		
	row = locals[cdt][cdn];
	row.amount = row.custom_amount;	
	
	if(row.qty!=undefined){				
		var area  = row.qty;
		var total = row.custom_amount;	
		row['rate'] = flt((total/area),2);
	}
	for(key in frm.doc.items)
	{			
//		var item = cur_frm.doc.items[key]	
		if(key.custom_amount != undefined)
		{
			totals  = totals + key.custom_amount;				
		}
	}
	cur_frm.set_value("total", totals);	
	cur_frm.set_value("grand_total", totals);
	cur_frm.refresh_fields();
})


frappe.ui.form.on("Sales Order Item", "amount", function(frm, cdt, cdn) //Created by Amitha M.D.
{		
	row = locals[cdt][cdn];
	if(row.qty!=undefined){				
		var area  = row.qty;
		var total = row.amount;	
/*		var grand_total= frm.doc.grand_total;		
				
//		long_rate  =  flt((total/area),10);	
//		small_rate =  flt((total/area),2);	
//		
//		r= flt((total/area),2);
		row['rate'] = flt((total/area),2);
		
//		row['amount'] = rate* area;
	//	frappe.model.set_value(cdt, cdn, "item_rate", rate);		
		
		
//		var n = rate.toFixed(2);
//		row.rate = n;
//		row.rate= long_rate;
//		row.amount =flt((long_rate * area),0); // Re-assigning amount when changes according to Qty * Rate //Headache :-> 
	////	row.amount = Math.round(100*total)/100;
		
//		doc.rounded_total=Math.round(100*total)/100;
		
//		d.amount = n * d.qty
		
		//cur_frm.refresh_fields();
		
		var totals=0;
		for(key in frm.doc.items)
		{			
			var item = cur_frm.doc.items[key]	
			if(item.amount != undefined)
			{
					totals  = totals + item.amount;				
			}
		}
		cur_frm.set_value("total", totals);	
		cur_frm.set_value("grand_total", totals);
			
			
//		rounded_total_amount =  Math.round(totals * 100) /100;
		rounded_total_amount = (Math.round(totals * 10) / 10).toFixed(2)
		discount = frm.doc.total - frm.doc.rounded_total;
		
		cur_frm.set_value("rounded_total",rounded_total_amount);
//		cur_frm.set_value("discount_amount",discount);
		cur_frm.refresh_fields();
		//frm.refresh();		*/
		row['rate'] = flt((total/area),2);
		cur_frm.refresh_fields();
	}	
});

