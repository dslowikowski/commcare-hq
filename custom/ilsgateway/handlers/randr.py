from datetime import datetime

from custom.ilsgateway.handlers import get_location
from custom.ilsgateway.models import SupplyPointStatus, SupplyPointStatusTypes, SupplyPointStatusValues, \
    DeliveryGroupReport
from custom.ilsgateway.handlers.keyword import KeywordHandler


class RandrHandler(KeywordHandler):

    def handle(self):
        self._handle()

    def help(self):
        self._handle(help=True)

    def _handle(self, help=False):
        location = get_location(self.domain, self.user, None)
        status_type = None
        if location['location'].location_type == 'FACILITY':
            status_type = SupplyPointStatusTypes.R_AND_R_FACILITY
        elif location['location'].location_type == 'DISTRICT':
            if help:
                quantities = [0, 0, 0]
            else:
                quantities = [self.args[1], self.args[3], self.args[5]]
            status_type = SupplyPointStatusTypes.R_AND_R_DISTRICT
            DeliveryGroupReport.objects.create(
                supply_point=location['case']._id,
                quantity=quantities[0],
                message=self.msg._id,
                delivery_group="A")
            DeliveryGroupReport.objects.create(
                supply_point=location['case']._id,
                quantity=quantities[1],
                message=self.msg._id,
                delivery_group="B")
            DeliveryGroupReport.objects.create(
                supply_point=location['case']._id,
                quantity=quantities[2],
                message=self.msg._id,
                delivery_group="C")
        SupplyPointStatus.objects.create(supply_point=location['case']._id,
                                         status_type=status_type,
                                         status_value=SupplyPointStatusValues.SUBMITTED,
                                         status_date=datetime.utcnow())