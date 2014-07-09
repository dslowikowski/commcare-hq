from datetime import datetime
import logging

from django.core.urlresolvers import reverse
from django.utils import html
from django.utils.translation import ugettext as _, ugettext_noop
import simplejson

from corehq.apps.api.es import ReportCaseES
from corehq.apps.cloudcare.api import get_cloudcare_app, get_cloudcare_form_url
from corehq.apps.reports.datatables import DataTablesHeader, DataTablesColumn
from corehq.apps.reports.filters.search import SearchFilter
from corehq.apps.reports.generic import ElasticProjectInspectionReport
from corehq.apps.reports.standard import CustomProjectReport, ProjectReportParametersMixin
from corehq.apps.reports.standard.cases.basic import CaseListMixin
from corehq.apps.reports.standard.cases.data_sources import CaseDisplay
from corehq.elastic import es_query
from corehq.pillows.base import restore_property_dict
from corehq.pillows.mappings.reportcase_mapping import REPORT_CASE_INDEX
from custom.succeed import PatientInfoReport
from custom.succeed.reports import VISIT_SCHEDULE, LAST_INTERACTION_LIST, EMPTY_FIELD, \
    INPUT_DATE_FORMAT, OUTPUT_DATE_FORMAT, CM_APP_VIEW_UPDATE_TASK_MODULE, CM_UPDATE_TASK, TASK_RISK_FACTOR, \
    TASK_ACTIVITY
from custom.succeed.utils import is_succeed_admin, has_any_role, SUCCEED_CM_APPNAME, get_app_build, get_form_url
from casexml.apps.case.models import CommCareCase
from dimagi.utils.decorators.memoized import memoized


class PatientTaskListReportDisplay(CaseDisplay):
    def __init__(self, report, case_dict):
        self.domain = report.domain
        self.app_dict = get_cloudcare_app(self.domain, SUCCEED_CM_APPNAME)
        self.latest_build = get_app_build(self.app_dict)
        super(PatientTaskListReportDisplay, self).__init__(report, case_dict)

    def get_link(self, url, field):
        if url:
            return html.mark_safe("<a class='ajax_dialog' href='%s' target='_blank'>%s</a>" % (url, html.escape(field)))
        else:
            return "%s (bad ID format)" % field

    @property
    @memoized
    def full_name(self):
        indices = self.case.get("indices", EMPTY_FIELD)

        if indices == EMPTY_FIELD:
            return EMPTY_FIELD

        return CommCareCase.get(indices[0]["referenced_id"])["full_name"]

    @property
    def full_name_url(self):
        return html.escape(
                PatientInfoReport.get_url(*[self.case["domain"]]) + "?patient_id=%s" % self.case["indices"][0]["referenced_id"])

    @property
    def full_name_link(self):
        return self.get_link(self.full_name_url, self.full_name)

    @property
    def name(self):
        return self.case.get("name", EMPTY_FIELD)

    @property
    def name_url(self):
        if self.status == "Closed":
            url = reverse('case_details', args=[self.domain, self.case["_id"]])
            return url + '#!history'
        else:
            return get_form_url(self.app_dict, self.domain, self.latest_build, CM_APP_VIEW_UPDATE_TASK_MODULE, CM_UPDATE_TASK, self.case["_id"])


    @property
    def name_link(self):
        return self.get_link(self.name_url, self.name)

    @property
    def task_responsible(self):
        return self.case.get("task_responsible", EMPTY_FIELD)

    @property
    def case_filter(self):
        filters = []
        care_site = self.request_params.get('task_responsible', '')
        if care_site != '':
            filters.append({'term': {'task_responsible.#value': care_site.lower()}})
        return {'and': filters} if filters else {}

    @property
    def status(self):
        return self.case.get("closed") and "Closed" or "Open"

    @property
    def task_due(self):
        rand_date = self.case.get("task_due", EMPTY_FIELD)
        if rand_date != EMPTY_FIELD:
            date = datetime.strptime(rand_date, INPUT_DATE_FORMAT)
            return date.strftime(OUTPUT_DATE_FORMAT)
        else:
            return EMPTY_FIELD

    @property
    def last_modified(self):
        rand_date = self.case.get("last_updated", EMPTY_FIELD)
        if rand_date != EMPTY_FIELD:
            date = datetime.strptime(rand_date, INPUT_DATE_FORMAT)
            return date.strftime(OUTPUT_DATE_FORMAT)
        else:
            return EMPTY_FIELD

    @property
    def task_activity(self):
        key = self.case.get("task_activity", EMPTY_FIELD)
        return TASK_ACTIVITY.get(key, key)

    @property
    def task_risk_factor(self):
        key = self.case.get("task_risk_factor", EMPTY_FIELD)
        return TASK_RISK_FACTOR.get(key, key)

    @property
    def task_details(self):
        return self.case.get("task_details", EMPTY_FIELD)


class PatientTaskListReport(CustomProjectReport, CaseListMixin, ElasticProjectInspectionReport, ProjectReportParametersMixin):
    ajax_pagination = True
    name = ugettext_noop('Patient Tasks')
    slug = 'patient_task_list'
    default_sort = {'task_due.#value': 'asc'}
    base_template_filters = 'succeed/report.html'
    case_type = 'task'

    fields = ['custom.succeed.fields.ResponsibleParty',
              'custom.succeed.fields.PatientName',
              'custom.succeed.fields.TaskStatus',
              'corehq.apps.reports.standard.cases.filters.CaseSearchFilter']

    @classmethod
    def show_in_navigation(cls, domain=None, project=None, user=None):
        if domain and project and user is None:
            return True
        if user and (is_succeed_admin(user) or has_any_role(user)):
            return True
        return False

    @property
    @memoized
    def rendered_report_title(self):
        return self.name

    @property
    @memoized
    def case_es(self):
        return ReportCaseES(self.domain)

    @property
    def headers(self):
        headers = DataTablesHeader(
            DataTablesColumn(_("Patient Name")),
            DataTablesColumn(_("Task Name"), prop_name="name"),
            DataTablesColumn(_("Responsible Party"), prop_name="task_responsible", sortable=False),
            DataTablesColumn(_("Status"), prop_name='status', sortable=False),
            DataTablesColumn(_("Action Due"), prop_name="task_due.#value"),
            DataTablesColumn(_("Last Update"), prop_name='last_updated.#value'),
            DataTablesColumn(_("Task Type"), prop_name="task_activity"),
            DataTablesColumn(_("Associated Risk Factor"), prop_name="task_risk_factor.#value"),
            DataTablesColumn(_("Details"), prop_name="task_details", sortable=False),
        )
        return headers

    def get_visit_script(self, responsible_party):
        return {
            "script":
                """
                    next_visit=visits_list[0];
                    before_action=null;
                    count=0;
                    foreach(visit : visits_list) {
                        skip = false;
                        foreach(action : _source.actions) {
                            if (!skip && visit.xmlns.equals(action.xform_xmlns) && !action.xform_id.equals(before_action)) {
                                next_visit=visits_list[count+1];
                                before_visit=action.xform_id;
                                skip=true;
                                count++;
                            }
                            before_visit=action.xform_id;
                        }
                    }
                    return next_visit.get('responsible_party').equals(responsible_party);
                """,
            "params": {
                "visits_list": VISIT_SCHEDULE,
                "responsible_party": responsible_party
            }
        }

    @property
    @memoized
    def es_results(self):
        q = { "query": {
                "filtered": {
                    "query": {
                        "match_all": {}
                    },
                    "filter": {
                        "and": [
                            {"term": { "domain.exact": "succeed" }},
                        ]
                    }
                }
            },
            'sort': self.get_sorting_block(),
            'from': self.pagination.start if self.pagination else None,
            'size': self.pagination.count if self.pagination else None,
        }
        search_string = SearchFilter.get_value(self.request, self.domain)
        es_filters = q["query"]["filtered"]["filter"]

        responsible_party = self.request_params.get('responsible_party', '')
        if responsible_party:
            if responsible_party == 'Care Manager':
                es_filters["and"].append({"term": {"task_responsible.#value": "cm"}})
            else:
                es_filters["and"].append({"term": {"task_responsible.#value": "chw"}})


        task_status = self.request_params.get('task_status', '')
        if task_status:
            if task_status == 'closed':
                es_filters["and"].append({"term": {"closed": True}})
            else:
                es_filters["and"].append({"term": {"closed": False}})

        patient_id = self.request_params.get('patient_id', '')
        if patient_id:
            es_filters["and"].append({"term": {"indices.referenced_id": patient_id}})

        def _filter_gen(key, flist):
            return {"terms": {
                key: [item.lower() for item in flist if item]
            }}

        user = self.request.couch_user
        if not user.is_web_user():
            owner_ids = user.get_group_ids()
            user_ids = [user._id]
            owner_filters = _filter_gen('owner_id', owner_ids)
            user_filters = _filter_gen('user_id', user_ids)
            filters = filter(None, [owner_filters, user_filters])
            subterms = []
            subterms.append({'or': filters})
            es_filters["and"].append({'and': subterms} if subterms else {})

        if self.case_type:
            es_filters["and"].append({"term": {"type.exact": 'task'}})
        if search_string:
            query_block = {"queryString": {"query": "*" + search_string + "*"}}
            q["query"]["filtered"]["query"] = query_block

        logging.info("ESlog: [%s.%s] ESquery: %s" % (self.__class__.__name__, self.domain, simplejson.dumps(q)))

        if self.pagination:
            return es_query(q=q, es_url=REPORT_CASE_INDEX + '/_search', dict_only=False, start_at=self.pagination.start)
        else:
            return es_query(q=q, es_url=REPORT_CASE_INDEX + '/_search', dict_only=False)

    @property
    def get_all_rows(self):
        return self.rows

    @property
    def rows(self):
        case_displays = (PatientTaskListReportDisplay(self, restore_property_dict(self.get_case(case)))
                         for case in self.es_results['hits'].get('hits', []))

        for disp in case_displays:
            yield [
                disp.full_name_link,
                disp.name_link,
                disp.task_responsible,
                disp.status,
                disp.task_due,
                disp.last_modified,
                disp.task_activity,
                disp.task_risk_factor,
                disp.task_details
            ]

    @property
    def user_filter(self):
        return super(PatientTaskListReport, self).user_filter
