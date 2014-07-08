from custom.succeed.reports import PM_APP_PM_MODULE, PM3, PM4
from custom.succeed.reports.patient_details import PatientDetailsReport
from custom.succeed.utils import get_form_url


class PatientStatusReport(PatientDetailsReport):
    slug = "patient_status"
    name = 'Patient Status'

    @property
    def report_context(self):
        self.report_template_path = "patient_status.html"
        ret = super(PatientStatusReport, self).report_context
        ret['disenroll_patient_url'] = get_form_url(self.pm_app_dict, self.domain, self.latest_pm_build, PM_APP_PM_MODULE, PM3, ret['patient']['_id'])
        ret['change_patient_data_url'] = get_form_url(self.pm_app_dict, self.domain, self.latest_pm_build, PM_APP_PM_MODULE, PM4, ret['patient']['_id'])
        ret['view_mode'] = 'status'
        return ret