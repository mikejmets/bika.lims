from bika.lims import api
from bika.lims.browser import BrowserView
from bika.lims.numbergenerator import INumberGenerator
from zope.component import getUtility


class IDServerView(BrowserView):
    """ This browser view is to house ID Server related functions
    """

    def seed(self):
        """ Reset the number from which the next generated sequence start.
            If you seed at 100, next seed will be 101
        """
        form = self.request.form
        prefix = form.get('prefix', None)
        if prefix is None:
            return 'No prefix provided'
        seed = form.get('seed', None)
        if seed is None:
            return 'No seed provided'
        if not seed.isdigit():
            return 'Seed must be a digit'
        seed = int(seed)
        if seed < 0:
            return 'Seed cannot be negative'
        seed = seed - 1
        number_generator = getUtility(INumberGenerator)
        new_seq = number_generator.set_number(key=prefix, value=seed)
        return 'IDServerView: "%s" seeded to %s' % (prefix, new_seq)

    def flush_id_server(self):
        """ Reset all ids in the number generator
        """
        form = self.request.form
        confirm = form.get('confirm', 'False').lower() == 'true'

        number_generator = getUtility(INumberGenerator)
        number_generator.flush()
        return 'Number generator flushed'
