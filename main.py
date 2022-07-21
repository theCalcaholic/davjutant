import json
import os
import traceback
import caldav
import vobject
from caldav import DAVClient
from caldav.lib.error import NotFoundError, PutError
from lxml.etree import _Element
import icalendar
import hashlib
from flask import Flask, request, Response

caldav_url = os.environ['CALDAV_URL']
caldav_user = os.environ['CALDAV_USER']
caldav_password = os.environ['CALDAV_PASSWORD']
client = caldav.DAVClient(url=caldav_url, username=caldav_user, password=caldav_password)
principal = client.principal()

app = Flask(__name__)

find_calendars_query = """<?xml version='1.0' encoding='UTF-8'?><x0:propfind xmlns:x0="DAV:"><x0:prop><x0:displayname /><x0:resourcetype /><x0:current-user-privilege-set /></x0:prop></x0:propfind>"""

writeable_calendars = []


def is_writeable(user_privilege_set: _Element):
    try:
        dav_privileges = map(
            lambda privs: privs.getchildren(),
            filter(lambda child: child.tag == '{DAV:}privilege', user_privilege_set.getchildren()))
        dav_privileges_flat = [child.tag for children in dav_privileges for child in children]
        return '{DAV:}write' in dav_privileges_flat and '{DAV:}write-content' in dav_privileges_flat
    except StopIteration:
        return False


def find_calendars(client: DAVClient, writeable_only=True):
    response = client.propfind(f"{caldav_url}/calendars/{caldav_user}/", find_calendars_query, depth=1)
    xml_results = response.find_objects_and_props()
    results = {}
    for url, result in xml_results.items():
        results[url] = {}
        if result is not None:
            for k, prop in result.items():
                if k == '{DAV:}displayname':
                    results[url]['displayname'] = prop.text
                elif k == '{DAV:}resourcetype':
                    results[url]['types'] = list(map(lambda p: p.tag, prop.getchildren()))
                elif k == '{DAV:}current-user-privilege-set':
                    results[url]['can-write'] = is_writeable(prop)

    return {k: v for k, v in results.items()
            if '{urn:ietf:params:xml:ns:caldav}calendar' in v['types']
            and (not writeable_only or v['can-write'])}


def clean_principal(principal: caldav.Principal):
    calendars: list[caldav.Calendar] = principal.calendars()
    if calendars:
        for cal in calendars:
            clean_calendar(cal)


def clean_calendar(calendar: caldav.Calendar):
    for c_event in calendar.events():
        ical = next(filter(lambda vob: vob.name == 'VEVENT', c_event.icalendar_instance.subcomponents))
        clean_event(ical)


def clean_event(event: icalendar.Event):
    dirty = 'ORGANIZER' in event or event.get('attendee', False) or any(map(lambda comp: comp.name == "VALARM", event.subcomponents))
    if 'ORGANIZER' in event:
        del event["ORGANIZER"]
    event["ATTENDEE"] = []
    event.subcomponents = filter(lambda comp: comp.name != "VALARM", event.subcomponents)
    return dirty


@app.route('/update_calendars')
def update_calendars():
    global writeable_calendars
    writeable_calendars = list(map(lambda url: caldav.Calendar(client, url), find_calendars(client, writeable_only=True)))
    calendar_names = list(map(lambda cal: str(cal.url), writeable_calendars))
    print(f"Found calendars: {calendar_names}")
    return json.dumps({"calendars": calendar_names})


# @app.route('/prune/calendar', methods=['POST'])
# def prune_calendar():
#     pass


@app.route('/prune/event', methods=['POST'])
def prune_event():
    if 'WEBHOOKS_SECRET' in os.environ:
        m = hashlib.sha256()
        m.update(request.data + os.environ['WEBHOOKS_SECRET'].encode())
        if request.headers.get('X-Nextcloud-Webhooks', None) != m.hexdigest():
            return Response('Unauthorized', 401)
        print("Authorization successful!")
    payload = request.json
    vobj = vobject.readOne(payload['objectData']['calendardata'])
    uid = vobj.vevent.uid.value

    for vcal in writeable_calendars:
        print(f"Searching calendar {str(vcal.url)}")
        try:
            vevent = vcal.event_by_uid(uid)
        except NotFoundError:
            continue

        try:
            cal_event = next(filter(lambda vob: vob.name == 'VEVENT', vevent.icalendar_instance.subcomponents))
        except StopIteration:
            print("No VEVENT object found!")
            return Response('Invalid request', 400)
        if clean_event(cal_event):
            print(f"Event needs cleaning. Applying changes...")
            try:
                vevent.save(no_create=True)
            except PutError:
                print(f"Error writing changes. Potential permission issue...")
                traceback.print_exc()
                return Response("Error writing changes. Potential permission issue...", 503)
        else:
            print(f"Event doesn't need to be cleaned. Leaving untouched...")
            return 'success'

    msg = 'Event was not found in accessible calendars'
    print(msg)
    return Response(msg, 200)


if __name__ == "__main__":
    update_calendars()

    app.run(host=os.environ.get('ADDRESS', '0.0.0.0'),
            port=int(os.environ.get('PORT', '80')),
            debug=os.environ.get('VERBOSE', 'false') == 'true')
