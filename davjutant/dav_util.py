import caldav
from caldav import DAVClient
import icalendar
from lxml.etree import _Element

find_calendars_query = """<?xml version='1.0' encoding='UTF-8'?>""" \
                       """<x0:propfind xmlns:x0="DAV:"><x0:prop>""" \
                       """<x0:displayname /><x0:resourcetype /><x0:current-user-privilege-set />""" \
                       """</x0:prop></x0:propfind>"""


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
    response = client.propfind(f"{client.url}/calendars/{client.username}/", find_calendars_query, depth=1)
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
    dirty = 'ORGANIZER' in event or event.get('ATTENDEE', False) or any(map(lambda comp: comp.name == "VALARM", event.subcomponents))
    if 'ORGANIZER' in event:
        del event["ORGANIZER"]
    event["ATTENDEE"] = []
    event.subcomponents = filter(lambda comp: comp.name != "VALARM", event.subcomponents)
    return dirty
