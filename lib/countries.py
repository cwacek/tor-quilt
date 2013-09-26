import json

__ccdata__ = None

def build_cc_data():
  global __ccdata__
  __ccdata__ = {'names': {}, 'alpha-2': {}}
  with open("lib/data/cc.json") as ccin:
    data = json.load(ccin)

    for country in data:
      __ccdata__['names'][country['name']] = country['country-code']
      __ccdata__['alpha-2'][country['alpha-2']] = country['country-code']

def get_country_code(identifier):
  """ Return the numeric country code for identifier, 
  or None if it can't be found """
  global __ccdata__

  if __ccdata__ is None:
    build_cc_data()

  if identifier in __ccdata__['alpha-2']:
    cc = __ccdata__['alpha-2'][identifier]
    print("Setting country code to {0} from {1}"
          .format(cc, identifier))
    return cc

  if identifier in __ccdata__['names']:
    cc = __ccdata__['names'][identifier]
    print("Setting country code to {0} from {1}"
          .format(cc, identifier))
    return cc

  return None
