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
export CALDAV_URL="https://my-caldav.backend"
export CALDAV_USER="my-caldav-user"
export CALDAV_PASSWORD="my-caldav-password"
export PORT="80" #optional
export ADDRESS="0.0.0.0" #optional
python main.py
```

Meant to be used with https://github.com/kffl/nextcloud-webhooks
