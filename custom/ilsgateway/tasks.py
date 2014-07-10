import logging
from celery.task import task, periodic_task
from corehq.apps.domain.models import Domain
from custom.ilsgateway.api import ILSGatewayEndpoint
from custom.ilsgateway.commtrack import bootstrap_domain,  \
    webusers_sync, smsusers_sync, products_sync

from custom.ilsgateway.models import MigrationCheckpoint


#@periodic_task(run_every=timedelta(days=1), queue=getattr(settings, 'CELERY_PERIODIC_QUEUE', 'celery'))
def migration_task():
    projects = Domain.get_all()
    for project in projects:
        if project.commtrack_settings and project.commtrack_settings.ilsgateway_config.is_configured:
            bootstrap_domain(project)

@task
def bootstrap_domain_task(domain):
    return bootstrap_domain(domain)
