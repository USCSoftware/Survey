'''
Created on Apr 23, 2011

@author: jmvidal
'''
import cgi
import os
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from google.appengine.api import memcache
from django.utils import simplejson as json
from datetime import tzinfo, timedelta, datetime #@UnresolvedImport

import logging



class MainPage(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            userInfo = ('<b>%s</b> <a href="%s">logout</a>') % (user.nickname(), users.create_logout_url('/'))
        else:
            templateValues = {'loginURL' : users.create_login_url(self.request.uri)}
            path = os.path.join(os.path.dirname(__file__), 'login.html')            
            self.response.out.write(template.render(path,templateValues))
            return
        templateValues ={'userInfo' : userInfo}
        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path,templateValues))
        
class Upload(db.Model):
    owner = db.UserProperty() #the logged-in user, the one who uploaded it
    ownerNickname = db.StringProperty()
    date = db.DateTimeProperty() #time of submission
    file = db.TextProperty() # the file, its a json string
    fileName = db.StringProperty()
    id = db.IntegerProperty()
    
class Accumulator(db.Model):
    counter = db.IntegerProperty()

q = Accumulator.all()
if q.get() == None:
    a = Accumulator()
    a.counter = 0
    a.put()
    q = Accumulator.all()

key = q.get().key()

def incrementCounter():
    obj = db.get(key)
    obj.counter += 1
    obj.put()
    return obj.counter

def getNextId():
    return db.run_in_transaction(incrementCounter)

def isInteger(x):
    try:
        int(x)
        return True
    except:
        return False

class DataHandler(webapp.RequestHandler): #/data/*
    def get(self,id):
        user = users.get_current_user()
        if user:
            userInfo = ('<b>%s</b> <a href="%s">logout</a>') % (user.nickname(), users.create_logout_url('/'))
        else:
            templateValues = {'loginURL' : users.create_login_url(self.request.uri)}
            path = os.path.join(os.path.dirname(__file__), 'login.html')            
            self.response.out.write(template.render(path,templateValues))
            return
        templateValues ={'userInfo' : userInfo}
        if (id == ""):
            templateValues['uploads'] = Upload.all().filter('owner =', user).order('-date')
            path = os.path.join(os.path.dirname(__file__), 'filelist.html')
            self.response.out.write(template.render(path,templateValues))
        else: #/data/3 return data in .csv format
            theFile = Upload.all().filter('id =',int(id)).get()
            logging.info("theFile=")
            logging.info(theFile)
            if theFile:
                contents = json.loads(theFile.file)
                self.response.headers['Content-Type'] = 'text/plain'
                questionKeys = [k for k in contents[0]['answers']]
                questionKeys.sort()
                self.response.out.write('"surveyId","surveyName"')
                for k in questionKeys:
                    self.response.out.write(',"%s"' % k)
                self.response.out.write('\n')                    
                for survey in contents:                
                    self.response.out.write('%s,%s' % (survey['surveyId'], survey['surveyName']))
                    for k in questionKeys:
                        ans = survey['answers'][k]
                        if isInteger(ans):
                            self.response.out.write(',%s' % ans)
                        else:
                            self.response.out.write(',"%s"' % ans)
                    self.response.out.write('\n')
            else:
                self.response.out.write('No survey with id=%s' % id)
            
    
    def post(self,id):
        file = self.request.get('file')
        fileName = self.request.get('filename')
        user = users.get_current_user()
        if not user: 
            return #only logged in users can post
        nickname = user.nickname() if user else None
        up = Upload(date=datetime.now(), owner=user, ownerNickname=nickname, file=file, fileName=fileName, id=getNextId())
        up.put()

        
application = webapp.WSGIApplication([('/data/(.*)', DataHandler),
                                      ('/.*', MainPage)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
