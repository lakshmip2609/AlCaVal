import json
import requests
from flask import Blueprint, render_template, redirect, request, flash, url_for, session, make_response
from werkzeug.datastructures import MultiDict
from .forms import TicketForm
from .. import oidc, get_userinfo

from resources.smart_tricks import askfor, DictObj

ticket_blueprint = Blueprint('tickets', __name__, template_folder='templates', static_folder='static')

@ticket_blueprint.route('/tickets/edit', methods=['GET', 'PUT', 'POST'])
@oidc.check
def create_ticket():
    user = get_userinfo()
    edit = bool(request.args.get('prepid'))
    clone = bool(request.args.get('clone'))
    prepid = request.args.get('prepid') if edit else request.args.get('clone') if clone else None
    creating_new = False if edit else True

    if (clone or edit) and request.method=='GET':
        # Check if ticket exists
        ticket = askfor.get('/api/tickets/get/' + prepid).json()
        if not ticket['success']:
            return make_response(ticket['message'], 404)

        res = askfor.get('/api/tickets/get_editable/%s' % prepid).json()
        formdata = res['response']['object']

        # workflow IDs to string
        workflows = formdata.get('workflow_ids')
        formdata.update({'workflow_ids': ", ".join([str(i) for i in workflows])})

        editing_info = res['response']['editing_info']
        session['ticket_data'] = formdata
        session['ticket_editingInfo'] = editing_info

    elif request.method=='GET':
        "Create TICKET"
        session['ticket_data'] = None

    form = TicketForm(data=MultiDict(session['ticket_data']))

    editInfo = session['ticket_editingInfo']
    olddata = session['ticket_data']
    common_keys = set(form._fields.keys()).intersection(set(editInfo.keys()))
    if edit:
        for field in common_keys:
            rkw_value = form._fields.get(field).render_kw
            if rkw_value:
                form._fields.get(field).render_kw.update({'disabled': not editInfo.get(field)})
            else:
                form._fields.get(field).render_kw = {'disabled': not editInfo.get(field)}
    if clone:
        form._fields.get('prepid').data = ""

    if form.validate_on_submit():
        data = form.data
        if creating_new:
            res = askfor.put('api/tickets/create', data=str(json.dumps(data)), headers=request.headers).json()
            if res['success']: flash(u'Success! Ticket created!', 'success')
        else:
            data.update({'status': olddata['status'], 
                         'history': olddata['history'],
                         'created_relvals': olddata['created_relvals']
                        })
            res = askfor.post('api/tickets/update', data=str(json.dumps(data)), headers=request.headers).json()
            if res['success']: flash(u'Success! Ticket updated!', 'success')

        if res['success']:
            return redirect(url_for('tickets.tickets', prepid=res['response'].get('prepid')))
        else:
            flash(res['message'], 'danger')
    return render_template('TicketEdit.html.jinja', user_name=user.response.fullname, form=form, createNew=creating_new)



# Tickets table
from .Table import ItemTable

@ticket_blueprint.route('/tickets', methods=['GET'])
@oidc.check
def tickets():
    user = get_userinfo()
    response = askfor.get('api/search?db_name=tickets' +'&'+ request.query_string.decode()).json()
    items = response['response']['results']
    table = ItemTable(items, classes=['table', 'table-hover'])
    itemdict = DictObj({value['_id']: value for value in items})
    return render_template('Tickets.html.jinja', user_name=user.response.fullname, table=table, userinfo=user.response, items = itemdict)