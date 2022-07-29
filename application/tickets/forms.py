import re
import ast
import json
from flask_wtf import FlaskForm
from wtforms import SubmitField, SelectField, StringField, FieldList, TextAreaField, IntegerField
from wtforms.validators import DataRequired, InputRequired, ValidationError, StopValidation, Length, NumberRange
from wtforms.widgets import TextArea
from wtforms import widgets

from markupsafe import Markup
from wtforms.widgets.core import html_params
from wtforms.fields.core import Label as BaseLabel
from core_lib.utils.global_config import Config
from core_lib.utils.common_utils import ConnectionWrapper
import requests

grid_cert = Config.get('grid_user_cert')
grid_key = Config.get('grid_user_key')
cmsweb_url = 'https://cmsweb.cern.ch'

class CustomSelect:
    """
    Borrowed from: https://stackoverflow.com/questions/44379016/disabling-one-of-the-options-in-wtforms-selectfield/61762617
    """

    def __init__(self, multiple=False):
        self.multiple = multiple

    def __call__(self, field, option_attr=None, **kwargs):
        if option_attr is None:
            option_attr = {}
        kwargs.setdefault("id", field.id)
        if self.multiple:
            kwargs["multiple"] = True
        if "required" not in kwargs and "required" in getattr(field, "flags", []):
            kwargs["required"] = True
        html = ["<select %s>" % html_params(name=field.name, **kwargs)]
        for option in field:
            attr = option_attr.get(option.id, {})
            html.append(option(**attr))
        html.append("</select>")
        return Markup("".join(html))

class GTDataRequired(object):
    """Validator for Common Prompt GT
    """
    def __init__(self, message=None):
        self.message = message
        self.field_flags = {}

    def __call__(self, form, field):
        hltgt = bool(form.data['hlt_gt'].strip()=='')
        if field.data and (not isinstance(field.data, str) or field.data.strip()) and not hltgt:
            return
        if hltgt:
            return

        if self.message is None:
            message = field.gettext("This field is required.")
        else:
            message = self.message

        field.errors[:] = []
        raise StopValidation(message)

class Label(BaseLabel):
    """
    An HTML form label.
    """
    def __init__(self, field_id, text, label_rkw={}):
        super().__init__(field_id, text)
        self.label_rkw = label_rkw

    def __call__(self, text=None, **kwargs):
        kwargs.update(**self.label_rkw)
        return super().__call__(text=None, **kwargs)

def SetLabel(myid, label, name, label_rkw):
    return Label(myid,
                label if label is not None else self.gettext(name.replace("_", " ").title()),
                label_rkw=label_rkw)

class SSelectField(SelectField):
    def __init__(self, label=None, label_rkw={}, **kw):
        super().__init__(label=label, **kw)
        self.label = SetLabel(self.id, label, kw['name'], label_rkw)

class SStringField(StringField):
    def __init__(self, label=None, label_rkw={}, **kw):
        super().__init__(label=label, **kw)
        self.label = SetLabel(self.id, label, kw['name'], label_rkw)

class STextAreaField(TextAreaField):
    def __init__(self, label=None, label_rkw={}, **kw):
        super().__init__(label=label, **kw)
        self.label = SetLabel(self.id, label, kw['name'], label_rkw)

class SIntegerField(IntegerField):
    def __init__(self, label=None, label_rkw={}, **kw):
        super().__init__(label=label, **kw)
        self.label = SetLabel(self.id, label, kw['name'], label_rkw)

class TicketForm(FlaskForm):
    label_rkw = {'class': 'col-form-label-sm'}
    classDict = {'class': 'form-control form-control-sm'}
    prepid = SStringField(
                render_kw=classDict | {'disabled':''},
                label="Prep ID",
                label_rkw = label_rkw
                )
    batch_name = SStringField('Batch Name',
                validators=[DataRequired(message="Please provide appropreate batch name")],
                render_kw = classDict | {"placeholder":"Subsystem name or DPG/POG. e.g. Tracker"},
                label_rkw = {'class': 'col-form-label-sm required'}
                )
    cmssw_release = SStringField('CMSSW Release',
                validators=[DataRequired(message="Please provide correct CMSSW release")],
                render_kw = classDict | {"placeholder":"E.g CMSSW_12_3_..."},
                label_rkw = {'class': 'col-form-label-sm required'}
                )
    jira_ticket = SSelectField('Jira Ticket', 
                choices=[["", "Select Jira ticket to associated with this"], ["None", "Select nothing for a moment"]],
                validators=[DataRequired(message="Please select Jira ticket out of given list. Or choose to create new")],
                widget=CustomSelect(),
                default='',
                render_kw = classDict | {'option_attr': {"jira_ticket-0": {"disabled": True, "hidden": True}} },
                label_rkw = label_rkw
                )
    label = SStringField('Label (--label)',
                render_kw = classDict | {'placeholder': 'This label will be included in ReqMgr2 workflow name'},
                label_rkw = label_rkw
                )

    title = SStringField('Title',
                validators=[],
                render_kw = classDict | {"placeholder":"Title/purpose of the validation"},
                label_rkw = label_rkw
                )
    cms_talk_link = SStringField('CMS-Talk link',
                validators=[],
                render_kw = classDict | {"placeholder":"Put a link from where this validation was requested"},
                label_rkw = label_rkw
                )
    hlt_gt = SStringField('Target HLT GT',
                validators=[],
                render_kw = classDict | {"id":"hlt_gt", "placeholder":"HLT target global tag"},
                label_rkw = label_rkw
                )
    common_prompt_gt = SStringField('Common Prompt GT',
                        validators=[GTDataRequired(message="Since you have chosen to use HLT global tag, you are required to provide common prompt global tag, which is to be used in RECO step of workflow")],
                        render_kw= classDict | {'placeholder': 'Global tag to be used in RECO step of HLT workflow'},
                        label_rkw = {'class': 'col-form-label-sm'}
                        )
    hlt_gt_ref = SStringField('Reference HLT GT',
                validators=[],
                render_kw = classDict | {"id":"hlt_gt_ref", "placeholder":"HLT reference global tag"},
                label_rkw = label_rkw
                )
    prompt_gt = SStringField('Target Prompt GT',
                render_kw = classDict | {'placeholder': 'Prompt target global tag'},
                label_rkw = label_rkw
                )
    prompt_gt_ref = SStringField('Reference Prompt GT',
                render_kw = classDict | {'placeholder': 'Prompt reference global tag'},
                label_rkw = label_rkw
                )
    express_gt = SStringField('Target Express GT',
                render_kw = classDict | {'placeholder': 'Express target global tag'},
                label_rkw = label_rkw
                )
    express_gt_ref = SStringField('Reference Express GT',
                render_kw = classDict | {'placeholder': 'Express reference global tag'},
                label_rkw = label_rkw
                )
    input_datasets = STextAreaField('Datasets', validators=[],
                        render_kw = classDict | {"rows": 6, 'style': 'padding-bottom: 5px;',
                        'placeholder': 'Comma or line separated datasets. e.g: \
                         \n/HLTPhysics/Run2022C-v1/RAW, /ZeroBias/Run2022C-v1/RAW \
                         \n/JetHT/Run2022C-v1/RAW'
                        },
                        label_rkw = label_rkw
                        )
    input_runs = STextAreaField('Run numbers', validators=[],
                        render_kw = classDict | {"rows": 10, 'style': 'padding-bottom: 5px;',
                        'placeholder': 'Comma separated list of run numbers e.g. 346512, 346513 \
                         \nOr\nLumisections in JSON format. e.g. {"354553": [[1, 300]]}',
                        'onkeyup': 'validateJSON_or_List(this.id)'
                        },
                        label_rkw = label_rkw
                        )

    # command = SStringField('Command (--command)',
    #             render_kw = classDict | {"placeholder":"Arguments that will be added to all cmsDriver commands"},
    #             label_rkw = {'class': 'col-form-label-sm'}
    #             )
    # command_steps = SStringField('Command Steps',
    #             render_kw = classDict | {"placeholder":"E.g. RAW2DIGI, L1Reco, RECO, DQM"},
    #             label_rkw = {'class': 'col-form-label-sm'}
    #             )
    cpu_cores = SIntegerField('CPU Cores (-t)', default=8, validators=[NumberRange(min=1, max=16)],
                render_kw = classDict,
                label_rkw = {'class': 'col-form-label-sm'}
                )

    memory = SIntegerField('Memory', default=16000, validators=[NumberRange(min=0, max=30000)],
                render_kw = classDict | {'step': 1000},
                label_rkw = {'class': 'col-form-label-sm'}
                )
    n_streams = SIntegerField('Streams (--nStreams)', default=2, validators=[NumberRange(min=0, max=16)],
                render_kw = classDict,
                label_rkw = {'class': 'col-form-label-sm'}
                )
    matrix_choices = [
        ['alca', 'alca'], ['standard', 'standard'], ['upgrade', 'upgrade'], 
        ['generator', 'generator'], ['pileup', 'pileup'], ['premix', 'premix'],
        ['extendedgen', 'extendedgen'], ['gpu', 'gpu']
    ]
    matrix = SSelectField('Matrix (--what)', choices=matrix_choices,
                           validators=[DataRequired()],
                           default='alca',
                           render_kw = classDict,
                           label_rkw = label_rkw
                        )
    workflow_ids = SStringField('Workflow IDs', validators=[DataRequired()],
                        default='6.13, 6.14',
                        render_kw = classDict | {'placeholder': 'Workflow IDs separated by comma. E.g. 1.1,1.2'},
                        label_rkw = {'class': 'col-form-label-sm required'}
                        )
    notes = STextAreaField('Notes',  
                           render_kw = classDict | {
                                "rows": 5,
                                'style': 'padding-bottom: 5px;',
                                'placeholder': "Description of the request. \
                                 TWiki links etc.."
                           },
                           label_rkw = label_rkw
                      )
    submit = SubmitField('Save Ticket')

    # Validators
    def validate_cmssw_release(self, field):
        url = f'https://api.github.com/repos/cms-sw/cmssw/releases/tags/{field.data}'
        status_code = requests.head(url).status_code
        if status_code != 200:
            raise ValidationError('CMSSW release is not valid!')

    def validate_input_datasets(self, field):
        test_datasets = field.data.replace(',', '\n').split('\n')
        test_datasets = list(map(lambda x: x.strip(), test_datasets))
        test_datasets = list((filter(lambda x: len(x)>5, test_datasets)))
        wrong_datasets = list()
        with ConnectionWrapper(cmsweb_url, grid_cert, grid_key) as dbs_conn:
            for dataset in test_datasets:
                regex = r'^/[a-zA-Z0-9\-_]{1,99}/[a-zA-Z0-9\.\-_]{1,199}/[A-Z\-]{1,50}$'
                if not re.fullmatch(regex, dataset):
                    wrong_datasets.append(dataset)
                    continue
                res = dbs_conn.api(
                        'GET',
                        f'/dbs/prod/global/DBSReader/datasets?dataset={dataset}'
                        )
                res = json.loads(res.decode('utf-8'))
                if not res: wrong_datasets.append(dataset)
        if wrong_datasets:
            raise ValidationError(f'Invalid datasets: {", ".join(wrong_datasets)}')
        if (not field.data) and self.input_runs.data:
            raise ValidationError(f"Input dataset field is required when 'Run numbers' are provided")

    def validate_input_runs(self, field):
        try:
            if field.data == '':
                test_runs = list()
            elif not ('{' in field.data and '}' in field.data):
                test_runs = list(map(lambda x: x.strip(), field.data.split(',')))
            elif isinstance(ast.literal_eval(field.data), dict):
                test_runs = list(ast.literal_eval((field.data)).keys())
            else: raise Exception
        except Exception as e:
            raise ValidationError('Accepted only comma separated list of runs \
                                    or JSON formatted lumisections')
        wrong_runs = list()
        with ConnectionWrapper(cmsweb_url, grid_cert, grid_key) as dbs_conn:
            for run in test_runs:
                if not re.fullmatch(r'^\d{6}$', run):
                    wrong_runs.append(run)
                    continue
                res = dbs_conn.api(
                        'GET',
                        f'/dbs/prod/global/DBSReader/runs?run_num={run}'
                        )
                res = json.loads(res.decode('utf-8'))
                if not res: wrong_runs.append(run)
        if wrong_runs:
            raise ValidationError(f'Invalid runs: {", ".join(wrong_runs)}')
        if (not field.data) and self.input_datasets.data:
            raise ValidationError(f"Run numbers field is required when 'Dataset' field is provided")