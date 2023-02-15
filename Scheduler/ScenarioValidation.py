import re

from configparser import ConfigParser

from django.conf import settings

class ScenarioValidation(object):
    """ScenarioValidation
    Provides means to validate inputs in the application
    """

    def __init__(self):

        config = ConfigParser()
        config.read(settings.EEWSCENARIO_FOLDER + 'EEWScenarioConfig.cfg')

        self.magMin = config.get("EVENTLIMITS",'magMin') 
        self.magMax = config.get("EVENTLIMITS",'magMax')
        self.latMin = config.get("EVENTLIMITS",'latMin') 
        self.latMax = config.get("EVENTLIMITS",'latMax')
        self.lonMin = config.get("EVENTLIMITS",'lonMin') 
        self.lonMax = config.get("EVENTLIMITS",'lonMax')
        self.depthMin = config.get("EVENTLIMITS",'depthMin') 
        self.depthMax = config.get("EVENTLIMITS",'depthMax')
        self.magDepthExpr = config.get("REGEXP",'magDepthExpr')
        self.latLonExpr = config.get("REGEXP",'latLonExpr')


    def checkMagLimits(self, magnitude):
        if magnitude >= float(self.magMin) and magnitude <= float(self.magMax):
            return True
        return None

    def checkLatLimits(self, latitude):
        if latitude >= float(self.latMin) and latitude <= float(self.latMax):
            return True
        return None

    def checkLonLimits(self, longitude):
        if longitude >= float(self.lonMin) and longitude <= float(self.lonMax):
            return True
        return None

    def checkDepthLimits(self, depth):
        if depth >= float(self.depthMin) and depth <= float(self.depthMax):
            return True
        return None

    def checkYearLimits(self, year):
        if year >= 1800 and year <= 2021:
            return True
        return None

    def checkDayLimits(self, day):
        if day > 0 and day < 32:
            return True
        return None

    def checkMonthLimits(self, month):
        if month > 0 and month < 13:
            return True
        return None

    def checkHourLimits(self, hour):
        if hour >= 0 and hour < 24:
            return True
        return None

    def checkMinuteSecondLimits(self, minOrSec):
        if minOrSec >= 0 and minOrSec < 60:
            return True
        return None

    def validateBuiltEvent(self, BuiltEEWEvent):
        errorMsg = ""

        dayMonthHourMinuteSecondExpr = "^([0-9]{1,2})$"
        yearExpr = "^([0-9]{4})$"

        validMag = re.compile(self.magDepthExpr)
        if validMag.match(BuiltEEWEvent.eventMagnitude):
            if not self.checkMagLimits(float(BuiltEEWEvent.eventMagnitude)):
                errorMsg = "Magnitude not within limits for processing"
        else:
            errorMsg = "Incorrect format:  Magnitude"

        validLat = re.compile(self.latLonExpr)
        if validLat.match(BuiltEEWEvent.eventLatitude):
            if not self.checkLatLimits(float(BuiltEEWEvent.eventLatitude)):
                errorMsg = "Latitude not within limits for processing"
        else:
            errorMsg = "Incorrect format:  Latitude"

        validLon = re.compile(self.latLonExpr)
        if validLon.match(BuiltEEWEvent.eventLongitude):
            if not self.checkLonLimits(float(BuiltEEWEvent.eventLongitude)):
                errorMsg = "Longitude not within limits for processing"
        else:
            errorMsg = "Incorrect format:  Longitude"

        validDepth = re.compile(self.magDepthExpr)
        if validDepth.match(BuiltEEWEvent.eventDepth):
            if not self.checkDepthLimits(float(BuiltEEWEvent.eventDepth)):
                errorMsg = "Depth not within limits for processing"
        else:
            errorMsg = "Incorrect format:  Depth"

        validDayMonthHourMinuteSecond = re.compile(dayMonthHourMinuteSecondExpr)
        if validDayMonthHourMinuteSecond.match(BuiltEEWEvent.eventOriginDay):
            if not self.checkDayLimits(int(BuiltEEWEvent.eventOriginDay)):
                errorMsg = "Day not valid"
        else:
            errorMsg = "Incorrect format:  Day"

        if validDayMonthHourMinuteSecond.match(BuiltEEWEvent.eventOriginMonth):
            if not self.checkMonthLimits(int(BuiltEEWEvent.eventOriginMonth)):
                errorMsg = "Month not valid"
        else:
            errorMsg = "Incorrect format:  Month"

        if validDayMonthHourMinuteSecond.match(BuiltEEWEvent.eventOriginHour):
            if not self.checkHourLimits(int(BuiltEEWEvent.eventOriginHour)):
                errorMsg = "Hour not valid"
        else:
            errorMsg = "Incorrect format:  Hour"

        if validDayMonthHourMinuteSecond.match(BuiltEEWEvent.eventOriginMinute):
            if not self.checkMinuteSecondLimits(int(BuiltEEWEvent.eventOriginMinute)):
                errorMsg = "Minute not valid"
        else:
            errorMsg = "Incorrect format:  Minute"

        if validDayMonthHourMinuteSecond.match(BuiltEEWEvent.eventOriginSecond):
            if not self.checkMinuteSecondLimits(int(BuiltEEWEvent.eventOriginSecond)):
                errorMsg = "Second not valid"
        else:
            errorMsg = "Incorrect format:  Second"

        validYear = re.compile(yearExpr)
        if validYear.match(BuiltEEWEvent.eventOriginYear):
            if not self.checkYearLimits(int(BuiltEEWEvent.eventOriginYear)):
                errorMsg = "Year not valid"
        else:
            errorMsg = "Incorrect format:  Year"

        return errorMsg
