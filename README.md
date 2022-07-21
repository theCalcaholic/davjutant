# davjutant

Provides callbacks for removing attendees, organizer and alerts from caldav events

## Installation

```sh
git clone https://github.com/theCalcaholic/davjutant.git
cd davjutant
pip install -r requirements.txt
```

## Usage

**The following code example is just meant for illustration purposes. Don't use with real credentials; they could for example leak into bash history.**

```sh
export FLASK_APP=davjutant
export CALDAV_URL="https://my-caldav.backend"
export CALDAV_USER="my-caldav-user"
export CALDAV_PASSWORD="my-caldav-password"
export PORT="80" #optional
export ADDRESS="0.0.0.0" #optional
export WEBHOOKS_SECRET="my-shared-secret" #optional
flask run
```

Alternatively, run davjutant with docker:

```sh
docker run \
  -e CALDAV_URL="https://my-caldav.backend" \ 
  -e CALDAV_USER="my-caldav-user" \
  -e CALDAV_PASSWORD="my-caldav-password" \
  -e ADDRESS="0.0.0.0" \
  -e WEBHOOKS_SECRET="my-shared-secret" \
  -p 80:80 \
  thecalcaholic/davjutant
```

Meant to be used with https://github.com/kffl/nextcloud-webhooks. Configure it like this:

```php
# config.php
{
// ...
  'webhooks_calendar_object_created_url' => 'http://davjutant-address:80/prune/event',
  'webhooks_calendar_object_updated_url' => 'http://davjutant-address:80/prune/event'
  'webhooks_secret' => 'my-shared-secret',
// ...
}
```
