from datetime import datetime
from custom.ilsgateway.handlers import get_location
from custom.ilsgateway.handlers.keyword import KeywordHandler
from custom.ilsgateway.models import SupplyPointStatus, SupplyPointStatusTypes, SupplyPointStatusValues
from custom.ilsgateway.reminders import DELIVERY_CONFIRM_DISTRICT, DELIVERY_PARTIAL_CONFIRM


class DeliveredHandler(KeywordHandler):
    def handle(self):
        location = get_location(self.domain, self.user, None)
        SupplyPointStatus.objects.create(supply_point=location['case']._id,
                                         status_type=SupplyPointStatusTypes.DELIVERY_FACILITY,
                                         status_value=SupplyPointStatusValues.RECEIVED,
                                         status_date=datetime.utcnow())

    def help(self):
        location = get_location(self.domain, self.user, None)
        status_type = None
        if location['location'].location_type == 'FACILITY':
            status_type = SupplyPointStatusTypes.DELIVERY_FACILITY
            #TODO
            #self._send_delivery_alert_to_facilities(sp)

            self.respond(DELIVERY_CONFIRM_DISTRICT, contact_name=self.user.first_name + " " + self.user.last_name,
                         facility_name=location['case'].name)
        elif location['location'].location_type == 'DISTRICT':
            status_type = SupplyPointStatusTypes.DELIVERY_DISTRICT
            self.respond(DELIVERY_PARTIAL_CONFIRM)
        SupplyPointStatus.objects.create(supply_point=location['case']._id,
                                         status_type=status_type,
                                         status_value=SupplyPointStatusValues.RECEIVED,
                                         status_date=datetime.utcnow())