# EEW Scenario Views - Version 2.2
# Gary Gann

import subprocess, pickle, os, logging, time, uuid, sys, threading, yaml

from multiprocessing import Process

from django.conf import settings

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, get_list_or_404
from django.template import RequestContext
from django.contrib.auth import authenticate, login
from django.urls import reverse
from django.core.files import File
from distutils.text_file import TextFile
from xml.etree.ElementTree import Element, SubElement, ElementTree, parse

from configparser import ConfigParser
from collections import OrderedDict

from AddNewUser import AddUserToConfigs
from ScenarioAMQProcessor import ScenarioAMQProcessor
from ScenarioValidation import ScenarioValidation

currentDate = time.strftime("%d%m%Y")
logger = logging.getLogger('EEWScenario')
hdlr = logging.FileHandler(settings.EEWSCENARIO_FOLDER + "logs/EEWScenario" + currentDate + ".log")
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(formatter)
logger.addHandler(hdlr)
logger.addHandler(stdout_handler)

logger.setLevel(logging.INFO)

config = ConfigParser()
config.read(settings.EEWSCENARIO_FOLDER + 'EEWScenarioConfig.cfg')
nextEventIDLocation = config.get("FILES",'nextEventIDLocation')
scenarioListLocation = config.get("FILES",'scenarioListLocation')
adminUsersLocation = config.get("FILES",'adminUsersLocation')
SAImageLocation = config.get("FILES",'SAImageLocation')
userPropertiesLocation = settings.AMQ_FOLDER + '/conf/users.properties'
userInfoPropertiesLocation = settings.AMQ_FOLDER + '/conf/userInfo.properties'
groupsPropertiesLocation = settings.AMQ_FOLDER + '/conf/groups.properties'
activeMQConfigLocation = settings.AMQ_FOLDER + '/conf/activemq.xml'

scenarioValidation = ScenarioValidation()

uniqueID = str(uuid.uuid1())

eventBuildFile = settings.EEWSCENARIO_FOLDER + "BuiltEvents/EventBuild" + uniqueID + ".xml"
eventListFile = settings.EEWSCENARIO_FOLDER + "BuiltEvents/eventList" + uniqueID + ".p"
chosenEventFile = settings.EEWSCENARIO_FOLDER + "BuiltEvents/chosenEvent" + uniqueID + ".p"
threadIDFile = settings.EEWSCENARIO_FOLDER + "BuiltEvents/thread" + uniqueID + ".p"


class TestEEWEvent():

    def __init__(self, eventNotes, eventID = "", fileLocation = "", description = "", magnitude = "", location = "", depth = "", devEvent = False, timeStamp = "now", originTime = "now"):
        self.eventID = eventID
        self.fileLocation = fileLocation
        self.description = description
        self.timeStamp = timeStamp
        self.originTime = originTime
        self.magnitude = magnitude
        self.location = location
        self.depth = depth
        self.eventNotes = eventNotes
        self.devEvent = devEvent

class BuiltEEWEvent():

    def __init__(self, eventID, eventMagnitude, eventLatitude, eventLongitude, eventDepth, eventOriginYear="2001", eventOriginMonth="01", eventOriginDay="01", eventOriginHour="01", eventOriginMinute="01", eventOriginSecond="01"):
        self.eventID = eventID
        self.eventMagnitude = eventMagnitude
        self.eventLatitude = eventLatitude
        self.eventLongitude = eventLongitude
        self.eventDepth = eventDepth
        self.eventOriginYear = eventOriginYear
        self.eventOriginMonth = eventOriginMonth
        self.eventOriginDay = eventOriginDay
        self.eventOriginHour = eventOriginHour
        self.eventOriginMinute = eventOriginMinute
        self.eventOriginSecond = eventOriginSecond


def loginUser(request):

    if authenticated(request):
        return HttpResponseRedirect(reverse('Scheduler:scheduleTest'))
    loginPage = True
    state = "Please log in below..."
    username = password = ''
    if 'sysMessage' not in request.session:
        sysMessage = ""
        with open(settings.EEWSCENARIO_FOLDER + 'SystemMessage.txt', 'r') as msgFile:
            for line in msgFile:
                sysMessage = sysMessage + (line.rstrip('\r'))
        request.session["sysMessage"] = sysMessage
    if request.POST:
        username = request.POST.get('username')
        password = request.POST.get('password')
        loginSuccess = authenticateUser(request, username, password)

        if loginSuccess is True:
            request.session["lastEncodingSelected"] = "textMessage"
            return scheduleTest(request, True)
        else:
            state = "Your username and/or password were incorrect."
            loginPage = False

    return render(request, 'auth.html',{'state':state, 'loginPage': loginPage})

def index(request):
    if authenticated(request):
        return HttpResponseRedirect(reverse('Scheduler:scheduleTest'))
    return loginUser(request)

def admin(request):
    if adminAccess(request):
        return HttpResponseRedirect(reverse('Scheduler:adminPage'))
    return loginUser(request)

def authenticateUser(request, username, password):
    with open(userPropertiesLocation, 'r') as userPropFile:
        userAcct = []
        authenticated = None
        for line in userPropFile:
            if ( not line == '\n' and not line.startswith('#') ):
                userAcct = line.split('=',1)
                if userAcct[0] == username:
                    if userAcct[1].rstrip() == password: # INITIALIZE USER
                        return initializeUser(request, username, password)
                    else:
                        return False


def initializeUser(request, username, password):
    request.session.set_expiry(3600)    # 15 minute session expiration for inactivity
    request.session["authenticated"] = True
    request.session["userID"] = username
    request.session["pass"] = password	
    request.session["userSSLPort"] = "No Port Specified"
    request.session["userStompPort"] = "No Port Specified"
    with open(userInfoPropertiesLocation, 'r') as userInfoPropFile:
        for line in userInfoPropFile:
            if not line.startswith('##'):
                userInfo = line.split('|')
                if userInfo[0] == username:
                    request.session["userTopicName"] = userInfo[1].rstrip()
                    request.session["userSSLPort"] = userInfo[2].rstrip()
                    request.session["userStompPort"] = userInfo[3].rstrip()
                    request.session["userFullName"] = userInfo[4].rstrip()
                    request.session["userServer"] = userInfo[5].rstrip()
                    request.session["devAcct"] = True if (userInfo[6].rstrip() == "1") else False
    with open(adminUsersLocation, 'r') as adminUsersPropFile:
        admins = adminUsersPropFile.read()
        request.session["adminAcct"] = (True if (username in admins) else False)

    userTopicName = request.session["userTopicName"]
    welcomeMessage = "Welcome %s!"

    request.session["welcomeMessage"] = welcomeMessage % username

    request.session["SAImageLocation"] = SAImageLocation

    request.session["magMin"] = scenarioValidation.magMin
    request.session["magMax"] = scenarioValidation.magMax
    request.session["latMin"] = scenarioValidation.latMin
    request.session["latMax"] = scenarioValidation.latMax 
    request.session["lonMin"] = scenarioValidation.lonMin	
    request.session["lonMax"] = scenarioValidation.lonMax
    request.session["depthMin"] = scenarioValidation.depthMin
    request.session["depthMax"] = scenarioValidation.depthMax
    request.session["magDepthExpr"] = scenarioValidation.magDepthExpr.replace('\\','\\\\')
    request.session["latLonExpr"] = scenarioValidation.latLonExpr.replace('\\','\\\\')

    return True

def adminPage(request):
    if not authenticated(request):
        return logout(request)
    request.session["backURL"] = "Scheduler:loginUser"    	

    if request.method != 'POST': # If the form hasn't been submitted...
        return render(request, 'admin.html', {'showLogout':True, 'showReturn':True})

    try:
        newUser = {}
        newUser['newUserName'] = str(request.POST.get('newUserName'))
        newUser['newPassword'] = str(request.POST.get('newPassword'))
        newUser['newBrokerName'] = str(request.POST.get('newBrokerName'))
        newUser['SSLPort'] = str(request.POST.get('SSLPort'))
        newUser['autoPort'] = str(request.POST.get('autoPort'))
        newUser['webName'] = str(request.POST.get('webName'))
        newUser['server'] = str(request.POST.get('server'))
        newUser['devFlag'] = str(request.POST.get('devFlag'))
        newUser['userPropertiesLocation'] = userPropertiesLocation
        newUser['userInfoPropertiesLocation'] = userInfoPropertiesLocation
        newUser['groupsPropertiesLocation'] = groupsPropertiesLocation
        newUser['activeMQConfigLocation'] = activeMQConfigLocation

        for key, value in newUser.items(): 
            if not value:
                raise KeyError(key)

        confirmUserAdded = AddUserToConfigs(newUser)

        if not confirmUserAdded:
            return render(request, 'admin.html', 
                {
                    'error_message': "User not added properly",
                    'showLogout':True,
                    'showReturn':True
                })

    except KeyError as keyErr:
    # Redisplay the scheduling form.
        return render(request, 'admin.html', 
        {
        'error_message': keyErr.args,
        'showLogout':True,
        'showReturn':True
        })


    return render(request, 'addUserResults.html', 
    {
    'newUserName': newUser['newUserName'],
    'newBrokerName': newUser['newBrokerName'],
    'SSLPort': newUser['SSLPort'],
    'autoPort': newUser['autoPort'],
    'showLogout':True,
    'showReturn':True
    })


def scheduleTest(request, initialLogin=False):
    if not authenticated(request):
        return logout(request)
    devAcct = request.session["devAcct"]
    scenarioPermitted = False
    devEvent = False
    counter = 0

    with open(scenarioListLocation, 'r') as scenarioFile:
        scenarioCategories = ordered_load(scenarioFile, Loader=yaml.SafeLoader)
        eventList = list(scenarioCategories.items())


    pickle.dump(eventList, open(eventListFile,"wb" ) )
    if request.method != 'POST' or initialLogin: # If the form hasn't been submitted...
        return render(request, 'detail.html', {'event': eventList, 'showLogout':True, 'showAdmin':request.session["adminAcct"]})
    try:
        eventSelection = request.POST['EEWEvent'].split("|")
        eventID = eventSelection[0]
        executionTiming = "0"
        if eventSelection[1] == "event":
            messageType = ""
        else:
            messageType = eventSelection[1]
        encodingType = request.POST['messageEncoding']
    except KeyError:
    # Redisplay the scheduling form.
        return render(request, 'detail.html', 
        {
        'event': eventList, 
        'error_message': "You didn't select a choice.",
        'showLogout':True
        })
#    else:
        # Always return an HttpResponseRedirect after successfully dealing
        # with POST data. This prevents data from being posted twice if a
        # user hits the Back button.
    return scheduleResults(request, eventID, encodingType, messageType)


def scheduleResults(request, eventID, encodingType, messageType="", buildYourOwn=False):
    if not authenticated(request):
        return logout(request)

    timestamp = "now"
    originTime = "now-5"
    topicType = ".dm"
    sleepIntervals = []
    request.session["threadFile"] = threadIDFile

    if not buildYourOwn:
        request.session["backURL"] = "Scheduler:loginUser"
        catList = pickle.load( open(eventListFile,"rb" ) )
        for category, catEvents in catList:
            for event in catEvents:
                if event.get("uniqueID") == eventID:
                    chosenEvent = event
                    timestamp = event.get("timeStamp")
                    originTime = event.get("originTime")
                    eventFileLocation = settings.SCENARIOFILES_FOLDER + event.get("fileLocation")
                    if messageType:
                        eventFileLocation = eventFileLocation[:-4] + "_" + messageType + eventFileLocation[-4:]
                    break
    if messageType:
        topicType = ".gm-" + messageType
    else:
        messageType = "event"
    uniqueID = eventID + "." + str(uuid.uuid1())[:8]

    AMQValues = {
        'fileLocation': eventBuildFile if buildYourOwn else eventFileLocation,
        'userID': request.session.get('userID', ""),
        'passwd': request.session.get('pass', ""),
        'topicName': ("eew.test_" + request.session.get('userTopicName', "") + topicType + ".data"),
        'encoding': encodingType
    }

    try:
        nextEventID = "999"
        totalSleep = 0
        with open(nextEventIDLocation, 'r') as nextEventIDFile:
            nextEventID=nextEventIDFile.read().strip()

        AMQSender = ScenarioAMQProcessor(AMQValues)
        EEWDict = AMQSender.parseEEW()

        if buildYourOwn:
            request.session["backURL"] = "Scheduler:loginUser"
            chosenEvent = pickle.load( open(chosenEventFile,"rb" ) )
            AMQSender.sendAMQwithSTOMP(EEWDict)    
            return render(request, 'results.html', {'chosenEvent': chosenEvent, 'nextEventID': nextEventID, 'messageType': messageType, 'showLogout': True, 'showReturn':True})


        for key, value in EEWDict.items():
            msgSleep = int(value[0])
            totalSleep = totalSleep + msgSleep
            sleepIntervals.append((key,totalSleep,round(msgSleep/1000)))


        request.session["totalSleep"] = totalSleep
        logger.warning("totalSleep: " + str(totalSleep))
        t = StoppableThread(target=ScenarioProcessor, args=(request, AMQSender, EEWDict, totalSleep), daemon=False)

        with open(request.session["threadFile"], "w") as f:
            f.write("0")
        t.start()
    except Exception as e:
        print(str(e))
        logger.error(str(e))

    request.session["lastEventSelected"] = chosenEvent.get("uniqueID") + "|" + messageType
    request.session["lastEncodingSelected"] = encodingType
    request.session["chosenEvent"] = chosenEvent
    request.session["messageType"] = messageType
    request.session["sleepIntervals"] = sleepIntervals
    request.session["nextEventID"] = nextEventID


    return HttpResponseRedirect(reverse('Scheduler:checkProgress'))



def ScenarioProcessor(request, AMQSender, EEWDict, totalSleep):
    logger.warning("Thread started")
    p = Process(target=AMQSender.sendAMQwithSTOMP,
                                    args=(EEWDict,))
    p.start()
    processedStatus = {}
    currentTime = 0

    totalSleep = round(totalSleep/1000) + 5    # get the value in seconds plus 5 second buffer
    progressIntervals = round(totalSleep/10)

    for i in range(0, progressIntervals):
        if not os.path.exists(request.session["threadFile"]):
            p.terminate()
            logger.warning("Thread stopped at iteration " + str(i))
            return True
        percentDone = str(round((i/progressIntervals)*100))
        with open(request.session["threadFile"], "w") as f:
            f.write(percentDone)
            logger.warning("percentDone: " + percentDone)
        logger.warning("Sleeping for 10")
        time.sleep(10)

    os.remove(request.session["threadFile"])



def checkProgress(request):

    if 'Abort' in request.POST:
        logger.warning("Abort initiated")
        os.remove(request.session["threadFile"])
        del request.session["threadFile"]
        return HttpResponseRedirect(reverse('Scheduler:loginUser'))

    elif not os.path.exists(request.session["threadFile"]):
        del request.session["threadFile"]
        logger.warning("Process finished")
        return render(request, 'results.html', {'chosenEvent': request.session["chosenEvent"], 'nextEventID': request.session["nextEventID"], 'messageType': request.session["messageType"], 'showLogout': True, 'showReturn':True})


    with open (request.session["threadFile"], 'r') as f:
        percentDone = f.read().strip()
    logger.warning("Pt 2 percentDone: " + percentDone)
    return render(request, 'progress.html', {'sleepIntervals': request.session["sleepIntervals"], 'chosenEvent': request.session["chosenEvent"], 'nextEventID': request.session["nextEventID"], 'percentDone': percentDone, 'showLogout': True, 'showReturn':True})



def buildEvent(request, initialLogin=False):
    if not authenticated(request):
        return logout(request)
    devAcct = request.session["devAcct"]
    request.session["backURL"] = "Scheduler:loginUser"    	

    if request.method != 'POST' or initialLogin: # If the form hasn't been submitted...
        return render(request, 'buildEvent.html', {'showLogout':True, 'showReturn':True})
    try:
        builtEvent = BuiltEEWEvent("BuildYourOwnEvent", request.POST['eventMagnitude'], request.POST['eventLatitude'], request.POST['eventLongitude'], request.POST['eventDepth'])
        encodingType = request.POST['messageEncoding']

        invalidEventMessage = scenarioValidation.validateBuiltEvent(builtEvent)
        if invalidEventMessage:
            return render(request, 'buildEvent.html', 
            {
                'error_message': invalidEventMessage,
                'showLogout':True,
                'showReturn':True
            })


        messageType = ""
        templateFile = "templates/BuildTemplate"
        if messageType:
            templateFile += "_" + messageType
        templateFile += ".xml"
        input_xml = open(settings.EEWSCENARIO_FOLDER + templateFile,'r')
        tree = parse(input_xml)
        root = tree.getroot()
        for coreElement in root.getiterator():		
            if coreElement.tag == "mag":
                coreElement.text = builtEvent.eventMagnitude
            if coreElement.tag == "lat":
                coreElement.text = builtEvent.eventLatitude
            if coreElement.tag == "lon":
                coreElement.text = builtEvent.eventLongitude
            if coreElement.tag == "depth":
                coreElement.text = builtEvent.eventDepth
        request.session["eventMagnitude"] = builtEvent.eventMagnitude
        request.session["eventLatitude"] = builtEvent.eventLatitude
        request.session["eventLongitude"] = builtEvent.eventLongitude
        request.session["eventDepth"] = builtEvent.eventDepth
        tree.write(eventBuildFile)


    except KeyError:
    # Redisplay the scheduling form.
        return render(request, 'buildEvent.html', 
        {
        'error_message': "You didn't select a choice.",
        'showLogout':True,
        'showReturn':True,
        'eventMagnitude':builtEvent.eventMagnitude,
        'eventLatitude':builtEvent.eventLatitude,
        'eventLongitude':builtEvent.eventLongitude,
        'eventDepth':builtEvent.eventDepth,
        })
#    else:
        # Always return an HttpResponseRedirect after successfully dealing
        # with POST data. This prevents data from being posted twice if a
        # user hits the Back button.
    chosenEvent = TestEEWEvent("Event created by the Build Your Own Event feature", builtEvent.eventID, "", "Custom Event", builtEvent.eventMagnitude, (builtEvent.eventLatitude + ", " + builtEvent.eventLongitude), builtEvent.eventDepth, False) 

    pickle.dump(chosenEvent, open(chosenEventFile,"wb" ) )

    return scheduleResults(request, builtEvent.eventID, encodingType, messageType, True)


def authenticated(request):
    if not request.session.get('authenticated', False):
        return False;
    else:
        return True;

def adminAccess(request):
    if not request.session.get('adminAcct', False):
        return False;
    else:
        return True;

def logout(request):
    request.session.flush()
    return loginUser(request)




def ordered_load(stream, Loader=yaml.SafeLoader, object_pairs_hook=OrderedDict):
    class OrderedLoader(Loader):
        pass
    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))
    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)
    return yaml.load(stream, OrderedLoader)

class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self,  *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()
        self.thread_id = threading.get_ident()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()
