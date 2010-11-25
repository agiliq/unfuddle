
import getpass
import simplejson
import sys
import urllib, urllib2

from datetime import datetime, date

try:
    from settings import *
except ImportError:
    ACCOUNT_DETAILS = {
        'account': '',
        'username': '', 
        'password': '',
    }
    SEND_MAIL = False

if not ACCOUNT_DETAILS['account']:
    ACCOUNT_DETAILS['account'] = raw_input('Enter unfuddle account name: ')

if not ACCOUNT_DETAILS['username']:
    ACCOUNT_DETAILS['username'] = raw_input('Username: ')

if not ACCOUNT_DETAILS['password']:
    ACCOUNT_DETAILS['password'] = getpass.getpass()


class BasicAuth(urllib.FancyURLopener):
    def __init__(self, *args, **kwargs):
        urllib.FancyURLopener.__init__(self, *args, **kwargs)
        self.maxtries = 2
        
    def prompt_user_passwd(self, host, realm):
        print 'Authentication failed please enter your username/password again'
        ACCOUNT_DETAILS['username'] = raw_input('Username: ')
        ACCOUNT_DETAILS['password'] = getpass.getpass()
        return ACCOUNT_DETAILS['username'], ACCOUNT_DETAILS['password']

    def http_error_401(self, url, fp, errcode, errmsg, headers, data=None):
        """Error 401 -- authentication required. This function supports Basic authentication only."""
        self.tries += 1
        if self.maxtries and self.tries >= self.maxtries:
            self.tries = 0
            return self.http_error_default(url, fp, 500, "HTTPS Basic Auth timed out after "+str(self.maxtries)+" attempts.", headers)
        return urllib.FancyURLopener.http_error_401(self, url, fp, errcode, errmsg, headers, data)
        
        
def valid_auth():
    url = 'https://%s.unfuddle.com/api/v1/projects/' % (ACCOUNT_DETAILS['account'])

    opener = BasicAuth() 
    opener.addheaders = [('Content-Type', 'application/xml'), ('Accept', 'application/json')] 
    
    response = opener.open(url)
    return response.code == 200


class Unfuddle(object):
    def __init__(self):
        self.base_url = 'https://%s.unfuddle.com' % (ACCOUNT_DETAILS['account'])
        self.api_base_path = '/api/v1/'

    def get_data(self, api_end_point):
        # url = 'https://agiliq.unfuddle.com/api/v1/projects'
        url = self.base_url + self.api_base_path + api_end_point

        auth_handler = urllib2.HTTPBasicAuthHandler() 
        auth_handler.add_password(realm='Unfuddle API', 
                                  uri=url, 
                                  user=ACCOUNT_DETAILS['username'], 
                                  passwd=ACCOUNT_DETAILS['password']) 

        opener = urllib2.build_opener(auth_handler) 
        opener.addheaders = [('Content-Type', 'application/xml'), ('Accept', 'application/json')] 

        # print '\n', url, '\n'
        try: 
            response = opener.open(url).read().strip() 
            # print 'response:', response 
            return simplejson.loads(response)
        except IOError, e: 
            print IOError, e
    
    def get_projects(self):
        return self.get_data('projects')

    def select_project(self):
        projects = self.get_projects()
        if len(projects) == 1:
            print 'There is only one project "%s"' % (projects[0]['title'])
            return projects[0]
        for index, project in enumerate(projects):
            print '%s. %s' % (index+1, project['title'])
        project_index = int(raw_input('Enter the project number: ')) - 1
        return projects[project_index]

    def get_tickets(self, project=None):
        if not project:
            project = self.select_project()
        api_end_point = 'projects/%s/tickets' % (project['id'])
        tickets = self.get_data(api_end_point)
        return project, tickets
    
    def dynamic_report(self, project=None, query_string=None):
        if project:
            api_end_point = 'projects/%s/ticket_reports/dynamic' % (project['id'])
        else:
            api_end_point = 'ticket_reports/dynamic'
        if query_string:
            api_end_point += '?%s' % (query_string)
        dynamic_report = self.get_data(api_end_point)
        return dynamic_report

def get_ticket_report():
    unfuddle = Unfuddle()
    project, tickets = unfuddle.get_tickets()
    print '\n'
    print 'Total tickets in project:', len(tickets)

    today_new_tickets = []
    today_resolved_tickets = []
    today_closed_tickets = []
    total_closed_tickets = 0
    total_resolved_tickets = 0
    total_pending_tickets = 0

    for ticket in tickets:
        if datetime.strptime(ticket['created_at'], '%Y-%m-%dT%H:%M:%SZ').date() == datetime.utcnow().date():
            today_new_tickets.append(ticket)
        elif datetime.strptime(ticket['updated_at'], '%Y-%m-%dT%H:%M:%SZ').date() == datetime.utcnow().date() and ticket['status'] == 'resolved':
            today_resolved_tickets.append(ticket)
        elif datetime.strptime(ticket['updated_at'], '%Y-%m-%dT%H:%M:%SZ').date() == datetime.utcnow().date() and ticket['status'] == 'closed':
            today_closed_tickets.append(ticket)

        if ticket['status'] == 'closed':
            total_closed_tickets += 1
        elif ticket['status'] == 'resolved':
            total_resolved_tickets += 1
        else:
            total_pending_tickets += 1
    
    print '\n'
    print 'Today new tickets:', len(today_new_tickets)
    print 'Today resolved tickets:', len(today_resolved_tickets)
    print 'Today closed tickets:', len(today_closed_tickets)
    print '\n'
    print 'Total closed tickets:', total_closed_tickets
    print 'Total resolved tickets:', total_resolved_tickets
    print 'Total pending tickets:', total_pending_tickets

    query_string = 'group_by=assignee'
    query_string += '&conditions_string=status-neq-closed,status-neq-resolved'
    dynamic_report = unfuddle.dynamic_report(project, query_string=query_string)
    
    print '\n'
    print 'Number of tickets in each person queue'
    for group in sorted(dynamic_report['groups'], cmp=lambda x, y: cmp(len(y['tickets']), len(x['tickets']))):
        if not group:
            continue
        print '\t', group['title'], ' ' * (25 - len(group.get('title', ''))), '-', len(group['tickets'])
    
    """
    query_string = 'group_by=assignee'
    query_string += '&conditions_string=status-eq-closed|status-eq-resolved' 
    # query_string += '&updated_at=%s' % (date.today().strftime('%Y-%m-%dT%H:%M:%SZ'))
    dynamic_report = unfuddle.dynamic_report(project, query_string=query_string)
    
    dynamic_report['new_groups'] = []
    for group in dynamic_report['groups']:
        new_group = group.copy()
        new_group['tickets'] = filter(lambda x: datetime.strptime(x['updated_at'], '%Y-%m-%dT%H:%M:%SZ').date() == datetime.utcnow().date(), group['tickets'])
        if new_group['title'] == 'Javed K.':
            print new_group
        dynamic_report['new_groups'].append(new_group)

    print '\n'
    print 'Number of tickets closed/resolved by each person today'
    for group in sorted(dynamic_report['new_groups'], cmp=lambda x, y: cmp(len(y['tickets']), len(x['tickets']))):
        if not group:
            continue
        print '\t', group['title'], ' ' * (25 - len(group.get('title', ''))), '-', len(group['tickets'])
    """

if __name__ == '__main__':
    if valid_auth():
        get_ticket_report()
    else:
        print 'Authentication failed..!!'
