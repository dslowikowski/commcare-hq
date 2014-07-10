from corehq.apps.commtrack.models import CommtrackConfig
from corehq.apps.commtrack.tests.util import CommTrackTest
from custom.ilsgateway.api import ILSGatewayEndpoint
from custom.ilsgateway.models import ILSGatewayConfig


class ILSGatewayBaseTest(CommTrackTest):

    def setUp(self):
        super(ILSGatewayBaseTest, self).setUp()
        self.api = ILSGatewayEndpoint('uri://mock/ils/endpoint', username='admin', password='password')

        ilsgateway_config = ILSGatewayConfig()
        ilsgateway_config.enabled = True

        commtrack_config = CommtrackConfig.for_domain(self.domain.name)
        commtrack_config.ilsgateway_config = ilsgateway_config
        commtrack_config.save()