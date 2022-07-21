import os
import traceback
import caldav
import vobject
from caldav.lib.error import NotFoundError, PutError
import icalendar
import hashlib
from flask import Flask, request, Response

caldav_url = os.environ['CALDAV_URL']
caldav_user = os.environ['CALDAV_USER']
caldav_password = os.environ['CALDAV_PASSWORD']
client = caldav.DAVClient(url=caldav_url, username=caldav_user, password=caldav_password)
principal = client.principal()

app = Flask(__name__)


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


# @app.route('/dav/prune/calendar', methods=['POST'])
# def prune_calendar():
#     pass


@app.route('/dav/prune/event', methods=['POST'])
def prune_event():
    if 'WEBHOOKS_SECRET' in os.environ:
        m = hashlib.sha256()
        m.update(request.data + os.environ['WEBHOOKS_SECRET'].encode())
        if request.headers.get('X-Nextcloud-Webhooks', None) != m.hexdigest():
            return Response('Unauthorized', 401)
        print("Authorization successful!")
    payload = request.json
    user = payload['calendarData']['principaluri'].split('/')[-1]
    calendar_uri = payload['calendarData']['uri']
    if user != caldav_user:
        calendar_uri = f"{calendar_uri}_shared_by_{user}"
    vobj = vobject.readOne(payload['objectData']['calendardata'])
    uid = vobj.vevent.uid.value
    try:
        print(f"cal url: {caldav_url}/calendars/{caldav_user}/{calendar_uri}")
        vcal = caldav.Calendar(client=client, url=f"{caldav_url}/calendars/{caldav_user}/{calendar_uri}")
        vevent = vcal.event_by_uid(uid)
    except NotFoundError:
        print(f"Unable to access event at '{caldav_url}/calendars/{user}/{calendar_uri}/{uid}")
        traceback.print_exc()
        return Response('Forbidden', 403)

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
            return Response("Error writing changes. Potential permission issue...", 403)
    else:
        print(f"Event doesn't need to be cleaned. Leaving untouched...")

    return 'success'


if __name__ == "__main__":

    app.run(host=os.environ.get('ADDRESS', '0.0.0.0'),
            port=int(os.environ.get('PORT', '80')),
            debug=os.environ.get('VERBOSE', 'false') == 'true')
