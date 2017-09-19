from bika.lims.browser import BrowserView
from bika.lims.numbergenerator import INumberGenerator
from zope.component import getUtility

class IDServerView(BrowserView):

    def seed(self):
        form = self.request.form
        prefix = form.get('prefix', None)
        if prefix is None:
            return
        seed = form.get('seed', None)
        if seed is None:
            return
        seed = int(seed)
        number_generator = getUtility(INumberGenerator)
        new_seq = number_generator.set_seed(key=prefix, seed=seed)


