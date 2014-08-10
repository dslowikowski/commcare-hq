from celery.task import task, periodic_task
from corehq.apps.domain.models import Domain
from custom.ilsgateway.commtrack import bootstrap_domain


#@periodic_task(run_every=timedelta(days=1), queue=getattr(settings, 'CELERY_PERIODIC_QUEUE', 'celery'))
from custom.ilsgateway.models import ILSGatewayConfig


def migration_task():
    configs = ILSGatewayConfig.get_all_domains()
    projects = []
    print configs
    for config in configs:
        if config.enabled:
            projects.append(config.domain)

    for project in projects:
        ilsgateway_config = ILSGatewayConfig.for_domain(project)
        if ilsgateway_config:
            bootstrap_domain(project, ilsgateway_config)


@task
def bootstrap_domain_task(domain):
    ilsgateway_config = ILSGatewayConfig.for_domain(domain)
    return bootstrap_domain(domain, ilsgateway_config)
