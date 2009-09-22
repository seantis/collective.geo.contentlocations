import csv, cStringIO
from zope import interface

from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope.app.pagetemplate import viewpagetemplatefile

from Products.CMFPlone.utils import getToolByName

from plone.z3cform import z2
from plone.z3cform.layout import wrap_form
from z3c.form import form, field, button
from z3c.form.interfaces import HIDDEN_MODE

from zope.component import getMultiAdapter

from collective.geo.contentlocations import ContentLocationsMessageFactory as _
from collective.geo.contentlocations.interfaces import IGeoManager
from collective.geo.contentlocations.interfaces import IGeoForm

from shapely.geos import ReadingError

class GeoShapeForm(form.Form):

    interface.implements(IGeoForm)

    template = viewpagetemplatefile.ViewPageTemplateFile('geoshapeform.pt')
    fields = field.Fields(IGeoManager).select('coord_type', 'filecsv', 'wkt')

    message_ok = _(u'Changes saved.')
    message_cancel = _(u'No changes made.')
    message_error_csv = _(u'CSV File not correct. Verify file format.')
    message_error_wkt = _(u'WKT expression not correct. Verify input.')
    message_error_input = _(u'No valid input given.')

    def __init__(self, context,  request):
        super(GeoShapeForm,  self).__init__(context,  request)
        self.geomanager = IGeoManager(self.context)

    @property
    def next_url(self):
        return self.context.absolute_url()

    def redirectAction(self):
        self.request.response.redirect(self.next_url)

    def setStatusMessage(self, message):
        ptool = getToolByName(self.context,'plone_utils')
        ptool.addPortalMessage(message)

    @button.buttonAndHandler(_(u'Save'))
    def handleApply(self, action):
        data, errors = self.extractData()

        if (errors):
            return

        ok, message = self.addCoordinates(data)
        if not ok:
            self.status = message
            return

        self.setStatusMessage(self.message_ok)
        self.redirectAction()

    @button.buttonAndHandler(_(u'Cancel'))
    def handleCancel(self, action):
        self.setStatusMessage(self.message_cancel)
        self.redirectAction()

    @property
    def geopoint_js(self):
        widget_id = self.widgets['wkt'].id
        return u"var wkt_widget_id='%s';\n" % widget_id

    def addCoordinates(self, data):
        """ from zgeo.geographer.README.txt
            Now set the location geometry to type "Point" and coordinates 105.08 degrees
            West, 40.59 degrees North using setGeoInterface()

            >>> geo.setGeoInterface('Point', (-105.08, 40.59))
        """
        filecsv = self.widgets['filecsv'].value
        if filecsv.tell():
            filecsv.seek(0)
            coords = self.csv2coordinates(filecsv.read())
            if coords:
                # should probably use dataconvert instead of array indexing
                shape = self.widgets['coord_type'].value[0]
                if shape.lower() == 'polygon':
                    # Polygon expects an outer hull and a hole.
                    coords = (coords, )
                self.geomanager.setCoordinates(shape, coords)
                return True, self.message_ok
            else:
                return False, self.message_error_csv
        else:
            try:
                geom = self.verifyWkt(data['wkt']).__geo_interface__
                self.geomanager.setCoordinates(geom['type'], geom['coordinates'])
                return True, self.message_ok
            except ReadingError:
                return False, self.message_error_wkt
        return False, self.message_error_input

    def verifyCsv(self,filecsv):
        reader = csv.reader(cStringIO.StringIO(str(filecsv)), delimiter=',')
        coords = []
        for row in reader:
            # check for row existence ???
            # are there any problems if the row is empty ???
            if row:
                # verify pairs of values are there
                try:
                    latitude = row[0]
                    longitude = row[1]
                except:
                    return False

                # verify that latitude and longitude are non-empty and non-zero
                if latitude != '' and longitude != '':
                    try:
                        # check for float convertible values
                        coords.append((float(latitude),float(longitude)))
                    except:
                        return False

        return coords

    def csv2coordinates(self, csv):
        csv_data = self.verifyCsv(csv)
        if csv_data != False:
            return tuple(csv_data)
        return False

    def verifyWkt(self, data):
        from shapely import wkt
        geom = wkt.loads(data);
        return geom

# TODO: maybe use geoform.pt as template/index
manageCoordinates = wrap_form(GeoShapeForm, label=_(u'Coordinates'),
                              description=_(u"Modify geographical data for this content"))
