from celery.schedules import crontab
from celery.task import periodic_task
import datetime
from casexml.apps.stock.models import StockTransaction
from corehq.apps.commtrack.models import SupplyPointCase, StockState
from corehq.apps.locations.models import Location, SQLLocation
from corehq.apps.products.models import SQLProduct
from corehq.apps.sms.api import send_sms_to_verified_number
from corehq.apps.users.models import CommCareUser
from custom.ewsghana.alerts import ONGOING_NON_REPORTING, ONGOING_STOCKOUT_AT_SDP, ONGOING_STOCKOUT_AT_RMS,\
    REPORT_REMINDER, DOMAIN, WEB_REMINDER, URGENT_NON_REPORTING, URGENT_STOCKOUT, COMPLETE_REPORT, INCOMPLETE_REPORT
from custom.ilsgateway.models import SupplyPointStatusTypes, SupplyPointStatusValues
from custom.ilsgateway.tanzania.reminders import update_statuses
import settings


def send_alert(transactions, sp, user, message):
    sp_ids = set()
    if sp and not transactions and user.get_verified_number():
        send_sms_to_verified_number(user.get_verified_number(), message)
        sp_ids.add(sp._id)
    update_statuses(sp_ids, SupplyPointStatusTypes.SOH_FACILITY, SupplyPointStatusValues.ALERT_SENT)

#Alert when facilities have not been reported continuously for 3 weeks
#@periodic_task(run_every=crontab(hour=10, minute=00),
#              queue=getattr(settings, 'CELERY_PERIODIC_QUEUE', 'celery'))
def on_going_non_reporting():
    sp_ids = set()
    now = datetime.datetime.utcnow()
    date = now - datetime.timedelta(days=21)
    for user in CommCareUser.by_domain(DOMAIN):
        if user.location and (user.location.location_type == 'district' or user.location.location_type == 'region'):
            facilities = user.location.children
            fac = set()
            if facilities:
                for facility in facilities:
                    sp = SupplyPointCase.get_by_location(facility)
                    if sp and not StockTransaction.objects.filter(
                            case_id=sp._id, type="stockonhand",
                            report__date__gte=date).exists() and user.get_verified_number():
                        fac.add(str(facility))
                        sp_ids.add(sp._id)
                if fac:
                    print ONGOING_NON_REPORTING % " \n".join(fac)
                    #send_sms_to_verified_number(user.get_verified_number(), ONGOING_NON_REPORTING % " \n".join(fac))
                    update_statuses(sp_ids, SupplyPointStatusTypes.SOH_FACILITY, SupplyPointStatusValues.REMINDER_SENT)


#Ongoing STOCKOUTS at SDP and RMS
#@periodic_task(run_every=crontab(hour=10, minute=25),
#              queue=getattr(settings, 'CELERY_PERIODIC_QUEUE', 'celery'))
def on_going_stockout():
    sp_ids = set()
    now = datetime.datetime.utcnow()
    date = now - datetime.timedelta(days=21)
    for user in CommCareUser.by_domain(DOMAIN):
        if user.location and (user.location.location_type == 'district'):
            facilities = user.location.children
            fac = set()
            if facilities:
                for facility in facilities:
                    sp = SupplyPointCase.get_by_location(facility)
                    if sp and StockTransaction.objects.filter(
                            case_id=sp._id, type="stockonhand", stock_on_hand=0, report__date__gte=date).exists() and \
                            user.get_verified_number():
                        fac.add(str(facility))
                        sp_ids.add(sp._id)
                if fac:
                    print ONGOING_STOCKOUT_AT_SDP % " \n".join(fac)
                    #send_sms_to_verified_number(user.get_verified_number(), ONGOING_STOCKOUT_AT_SDP " \n".join(fac))
                    update_statuses(sp_ids, SupplyPointStatusTypes.SOH_FACILITY, SupplyPointStatusValues.REMINDER_SENT)

        elif user.location and (user.location.location_type == 'region'):
            facilities = user.location.children
            fac = ()
            if facilities:
                for facility in facilities:
                    sp = SupplyPointCase.get_by_location(facility)
                    if sp and StockTransaction.objects.filter(
                            case_id=sp._id, type="stockout", stock_on_hand=0,
                            report__date__gte=date).exists() and user.get_verified_number():
                        fac.add(str(facility))
                        sp_ids.add(sp._id)
                if fac:
                    print ONGOING_STOCKOUT_AT_RMS % " \n".join(fac)
                    #send_sms_to_verified_number(user.get_verified_number(), ONGOING_STOCKOUT_AT_RMS " \n".join(fac))
                    update_statuses(sp_ids, SupplyPointStatusTypes.SOH_FACILITY, SupplyPointStatusValues.REMINDER_SENT)


#Urgent Non-Reporting
#@periodic_task(run_every=crontab(day_of_week=1, hour=8, minute=20),
#               queue=getattr(settings, 'CELERY_PERIODIC_QUEUE', 'celery'))
def urgent_non_reporting():
    sp_ids = set()
    now = datetime.datetime.utcnow()
    date = now - datetime.timedelta(days=21)
    for user in CommCareUser.by_domain(DOMAIN):
        if user.location and (user.location.location_type == 'district' or user.location.location_type == 'region'
                              or user.location.location_type == 'country'):
            facilities = user.location.children
            fac = set()
            no_rep = 0
            if facilities:
                for facility in facilities:
                    sp = SupplyPointCase.get_by_location(facility)
                    if sp and not StockTransaction.objects.filter(
                            case_id=sp._id, type="stockonhand",
                            report__date__gte=date).exists() and user.get_verified_number():
                        no_rep += 1
                        fac.add(str(facility))
                        sp_ids.add(sp._id)
                if fac and no_rep >= len(facilities)/2:
                    print URGENT_NON_REPORTING % user.location.name
                    #send_sms_to_verified_number(user.get_verified_number(), URGENT_NON_REPORTING % user.location.name)
                    update_statuses(sp_ids, SupplyPointStatusTypes.SOH_FACILITY, SupplyPointStatusValues.REMINDER_SENT)


#Urgent Stockout
#@periodic_task(run_every=crontab(day_of_week=1, hour=8, minute=20),
#               queue=getattr(settings, 'CELERY_PERIODIC_QUEUE', 'celery'))
def urgent_stockout():
    sp_ids = set()
    now = datetime.datetime.utcnow()
    date = now - datetime.timedelta(days=21)
    for user in CommCareUser.by_domain(DOMAIN):
        if user.location and (user.location.location_type == 'district' or user.location.location_type == 'region'
                              or user.location.location_type == 'country'):
            facilities = user.location.children
            fac = set()
            stocked_out_products = set()
            no_rep = 0
            if facilities:
                for facility in facilities:
                    sp = SupplyPointCase.get_by_location(facility)
                    if sp:
                        stocked_out = StockTransaction.objects.filter(
                        case_id=sp._id, type="stockonhand", stock_on_hand=0,
                        report__date__gte=date)
                        if stocked_out.exists() and user.get_verified_number():
                            no_rep += 1
                            fac.add(str(facility))
                            for product in stocked_out:
                                stocked_out_products.add(SQLProduct.objects.get(product_id=product.product_id).name)
                            sp_ids.add(sp._id)
                if fac and no_rep >= len(facilities):
                    print URGENT_STOCKOUT % (user.location.name,
                                             ", ".join(sorted([str(product) for product in stocked_out_products])))
                    #send_sms_to_verified_number(user.get_verified_number(), " ,".join(stocked_out_products))
                    update_statuses(sp_ids, SupplyPointStatusTypes.SOH_FACILITY, SupplyPointStatusValues.REMINDER_SENT)


#Web reminder, once every 3 months
#@periodic_task(run_every=crontab(month_of_year='1,4,7,10', day_of_month=1, hour=10, minute=3),
#               queue=getattr(settings, 'CELERY_PERIODIC_QUEUE', 'celery'))
def reminder_to_visit_website():
    for user in CommCareUser.by_domain(DOMAIN):
        if user.location and user.last_login < datetime.datetime.now() - datetime.timedelta(weeks=13) and\
                user.get_verified_number() \
                and (user.location.location_type == 'district' or user.location.location_type == 'region' or
                             user.location.location_type == 'country'):
                #send_sms_to_verified_number(user.get_verified_number(), WEB_REMINDER % user.name
                print WEB_REMINDER % user.name

#One week reminder when facility does not report to EWS
#@periodic_task(run_every=crontab(day_of_week=1, hour=11, minute=11),
#               queue=getattr(settings, 'CELERY_PERIODIC_QUEUE', 'celery'))
def report_reminder():
    sp_ids = set()
    now = datetime.datetime.utcnow()
    date = now - datetime.timedelta(days=7)
    for user in CommCareUser.by_domain(DOMAIN):
        if user.location:
            sp = SupplyPointCase.get_by_location(user.location)
            if sp and not StockTransaction.objects.filter(
                case_id=sp._id, type="stockonhand", report__date__gte=date).exists()\
                    and user.get_verified_number():
                sp_ids.add(sp._id)
                print REPORT_REMINDER % (user.name, user.location.name)
                #send_sms_to_verified_number(user.get_verified_number(),  \
                #REPORT_REMINDER % (user.name, user.location.name))
                update_statuses(sp_ids, SupplyPointStatusTypes.SOH_FACILITY, SupplyPointStatusValues.REMINDER_SENT)


#Checking if report was complete or not
def report_completion_check(sp_id, user):
    reported_products = StockTransaction.objects.filter(domain=DOMAIN, case_id=sp_id, type='stock_on_hand')
    expected_products = SQLProduct.objects.filter(domain=DOMAIN)
    reported_products_ = set()
    expected_products_ = set()
    for product in reported_products:
        reported_products_.add(SQLProduct.objects.get(product_id=product.product_id).name)
    for product in expected_products:
        expected_products_.add(SQLProduct.objects.get(product_id=product.product_id).name)
    missing_products = set.difference(reported_products_, expected_products_)
    if len(missing_products) == 0:
        print COMPLETE_REPORT
        #send_sms_to_verified_number(user.get_verified_number(), COMPLETE_REPORT)
    elif len(missing_products) != 0:
        print INCOMPLETE_REPORT % (user.name, user.location.name, ", ".join(sorted(missing_products)))
        #send_sms_to_verified_number(user.get_verified_number(), INCOMPLETE_REPORT % (user.name, user.location.name,
        # ", ".join(sorted(missing_products))))



