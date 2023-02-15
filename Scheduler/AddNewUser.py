from configparser import ConfigParser




def AddUserToConfigs(userToAdd):

    try:
        # extract info for new user to be added
        newUserName = userToAdd.get('newUserName')
        newPassword = userToAdd.get('newPassword')
        newBrokerName = userToAdd.get('newBrokerName')
        SSLPort = userToAdd.get('SSLPort')
        autoPort = userToAdd.get('autoPort')
        webName = userToAdd.get('webName')
        server = userToAdd.get('server')
        devFlag = userToAdd.get('devFlag')
        userPropertiesLocation = userToAdd.get('userPropertiesLocation')
        userInfoPropertiesLocation = userToAdd.get('userInfoPropertiesLocation')
        groupsPropertiesLocation = userToAdd.get('groupsPropertiesLocation')
        activeMQConfigLocation = userToAdd.get('activeMQConfigLocation')

        # groups add
        config = ConfigParser()
        config.read(groupsPropertiesLocation)
        config.set('GROUPS', newBrokerName, newUserName)
        everyone = config.get('GROUPS', 'everyone')
        everyone = everyone + "," + newUserName
        config.set('GROUPS', 'everyone', everyone)
        with open(groupsPropertiesLocation, 'w') as groupconfig:
            config.write(groupconfig)
        groupconfig.close()

        # users add
        userStr = '\n{0}={1}'.format(newUserName, newPassword)
        with open(userPropertiesLocation, 'r') as usersProp:
            usersStr = usersProp.read()
        if int(devFlag):
            index = usersStr.index('[DEVUSERS]') + len('[DEVUSERS]')
        else:
            index = usersStr.index('[EXTUSERS]') + len('[EXTUSERS]')
        newUsersStr = usersStr[:index] + userStr + usersStr[index:]
        with open(userPropertiesLocation, 'w') as userconfig:
            userconfig.write(newUsersStr)
        userconfig.close()

        # userInfo add
        userInfoStrToAdd = '{0}|{1}|{2}|{3}|{4}|{5}|{6}\n'.format(newUserName, newBrokerName, SSLPort, autoPort, webName, server, devFlag)
        with open(userInfoPropertiesLocation, 'a+') as newUserInfo:
            newUserInfo.write(userInfoStrToAdd)
        newUserInfo.close()

        # activemq.xml add
        authStr = '<authorizationEntry topic="eew.test_{0}.*.data" read="{0}" write="{0}" admin="{0}" />\n                  '.format(newBrokerName)
        with open(activeMQConfigLocation, 'r') as amqconfig:
            amqStr = amqconfig.read()
        index = amqStr.find('<authorizationEntry')
        newAmqStr = amqStr[:index] + authStr + amqStr[index:]
        with open(activeMQConfigLocation, 'w') as newAMQ:
            newAMQ.write(newAmqStr)
        newAMQ.close()

    except Exception as e:
        print(e)
        return False

    return True
