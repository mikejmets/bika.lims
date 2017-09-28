import logging
from bika.lims.browser import BrowserView
from bika.lims.numbergenerator import INumberGenerator
from zope.component import getUtility

logger = logging.getLogger("bika.lims.browser.idserver.view")

class IDServerView(BrowserView):

    def seed(self):
        """ You seed at 100, object added will start at 101
        """
        form = self.request.form
        prefix = form.get('prefix', None)
        if prefix is None:
            return
        seed = form.get('seed', None)
        if seed is None:
            return

        seed = int(seed) - 1
        number_generator = getUtility(INumberGenerator)
        new_seq = number_generator.set_seed(key=prefix, seed=seed)
        logger.debug('In IDServerView: new_seq is %s' % new_seq)
