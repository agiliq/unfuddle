from lamson.routing import route, route_like, stateless
from config.settings import UNFUDDLE_USERNAME, UNFUDDLE_PASSWORD
import httplib2, json

UNFUDDLE_API_ENDPOINT = "https://%(subdomain)s.unfuddle.com/api/v1"

@route("(subdomain)\+(project)@(host)", subdomain="\w+", project="\w+", host=".+")
def START(message, subdomain=None, project=None, host=None):
    UNFUDDLE_API_URL = UNFUDDLE_API_ENDPOINT %({"subdomain": subdomain})
    h = httplib2.Http()
    h.add_credentials(UNFUDDLE_USERNAME, UNFUDDLE_PASSWORD)
    _, content = h.request("%(url)s/projects.json" %({"url": UNFUDDLE_API_URL}), method="GET")
    json_content = json.loads(content)
    proj = None
    for proj_iter in json_content:
        if proj_iter["short_name"] == project:
            proj = proj_iter
    if not proj:
        return START
    _, tickets = h.request("%(url)s/projects/%(id)s/ticket_reports/dynamic.json?conditions_string=status-neq-closed"
                           %({"url": UNFUDDLE_API_URL, "id": proj["id"]}))
    ticket_json = json.loads(tickets)
    tickets = []
    if ticket_json["groups"]:
        tickets = ticket_json["groups"][0]["tickets"]
    for ticket in tickets:
        if ticket["summary"] == message.base["Subject"]:
            _, content = h.request("%(url)s/projects/%(id)s/tickets/%(ticket_id)s/comments"
                                   %({"url": UNFUDDLE_API_URL, "id": proj["id"], "ticket_id": ticket["id"]}),
                                   method="POST", 
                                   body="""<comment><body>%(body)s</body><body-format>plain</body-format></comment>""" 
                                   %{"body": message.body()},
                                   headers={"Accept": "application/xml", 
                                            "Content-Type": "application/xml"})
            return START
    _, content = h.request("%(url)s/projects/%(id)s/tickets" %({"url": UNFUDDLE_API_URL, "id": proj["id"]}), method="POST",
                           body="""<ticket><summary><![CDATA[%(summary)s]]></summary><description><![CDATA[%(description)s]]></description><description-format>plain</description-format><priority>3</priority></ticket>"""
                           %({"summary": message.base["Subject"], "description": message.body()}),
                           headers={"Accept": "application/xml", 
                                    "Content-Type": "application/xml"})
    return START


@route_like(START)
@stateless
def ERROR(message, subdomain=None, project=None, host=None):
    return START
