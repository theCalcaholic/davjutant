import json
import os
import traceback
import caldav
import vobject
from caldav.lib.error import NotFoundError, PutError
import hashlib
from flask import request, Response, Blueprint, current_app
from .dav_util import clean_event, find_calendars
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

writeable_calendars = []
dav_client = None

bp = Blueprint('routes', __name__, url_prefix='')


def require_client() -> caldav.DAVClient:
    global dav_client
    if dav_client is None:
        dav_client = caldav.DAVClient(
            url=current_app.config['CALDAV_URL'],
            username=current_app.config['CALDAV_USER'],
            password=current_app.config['CALDAV_PASSWORD'])
    return dav_client


@bp.route('/update-calendars')
@bp.before_app_first_request
def update_calendars():
    client = require_client()
    global writeable_calendars
    writeable_calendars = list(map(lambda url: caldav.Calendar(client, url), find_calendars(client, writeable_only=True)))
    calendar_names = list(map(lambda cal: str(cal.url), writeable_calendars))
    logger.info(f"Found calendars: {calendar_names}")
    return json.dumps({"calendars": calendar_names})


# @app.route('/prune/calendar', methods=['POST'])
# def prune_calendar():
#     pass

@bp.route('/prune/event', methods=['POST'])
def prune_event():
    if 'WEBHOOKS_SECRET' in os.environ:
        m = hashlib.sha256()
        m.update(request.data + os.environ['WEBHOOKS_SECRET'].encode())
        if request.headers.get('X-Nextcloud-Webhooks', None) != m.hexdigest():
            return Response('Unauthorized', 401)
        logger.info("Authorization successful!")
    payload = request.json
    vobj = vobject.readOne(payload['objectData']['calendardata'])
    uid = vobj.vevent.uid.value

    for vcal in writeable_calendars:
        logger.info(f"Searching calendar {str(vcal.url)}")
        try:
            vevent = vcal.event_by_uid(uid)
        except NotFoundError:
            continue

        try:
            cal_event = next(filter(lambda vob: vob.name == 'VEVENT', vevent.icalendar_instance.subcomponents))
        except StopIteration:
            logger.info("No VEVENT object found!")
            return Response('Invalid request', 400)
        if clean_event(cal_event):
            logger.info(f"Event needs cleaning. Applying changes...")
            try:
                vevent.save(no_create=True)
            except PutError:
                logger.info(f"Error writing changes. Potential permission issue...")
                traceback.print_exc()
                return Response("Error writing changes. Potential permission issue...", 503)
        else:
            logger.info(f"Event doesn't need to be cleaned. Leaving untouched...")
            return 'success'

    msg = 'Event was not found in accessible calendars'
    print(msg)
    return Response(msg, 200)

