# Fink Alert Broker Module for the TOM Toolkit

[![pypi](https://img.shields.io/pypi/v/tom-fink.svg)](https://pypi.python.org/pypi/tom-fink)

This repository hosts the Fink Alert Broker Module for the TOM Toolkit. Fink is a broker currently connected to ZTF. More information on Fink at https://fink-broker.org/.

As of version 0.2, the module simply uses the Fink REST API to retrieve alerts. Note that the Fink databases are updated once a day with the previous night alert data (hence you do not get live alerts for the moment). Users can perform:
- Search by ZTF object ID
- Cone Search
- Search by Date
- Search by derived alert class
- Search by Solar System name

## How to use the Fink module inside your TOM

First, install the module using pip

```bash
pip install tom-fink
```

then you need to declare it in your running TOM instance. To do so just add `tom_fink.fink.FinkBroker` to the `TOM_ALERT_CLASSES` in your TOM's `settings.py`:

```python
TOM_ALERT_CLASSES = [
  'tom_alerts.brokers.alerce.ALeRCEBroker',
  ...,
  'tom_fink.fink.FinkBroker'
]
```

and finally relaunch your TOM:

```bash
./manage.py runserver
```

## Todo list

- [ ] Add a test suite (preferably running on GitHub Actions)
- [x] Add a linter (preferably running on GitHub Actions)
- [x] Update the Query Form with all API features
- [ ] Enable querying livestreams using the Fink Kafka client
