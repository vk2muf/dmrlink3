#!/usr/bin/env python3
#
###############################################################################
#   Copyright (C) 2016-2019  Cortney T. Buffington, N0MJS <n0mjs@me.com>
###############################################################################

import json
from os.path import isfile, getmtime
from time import time
import urllib.request
from binascii import b2a_hex as ahex, unhexlify

# CONSTANTS
SUB_FIELDS   = ('ID', 'CALLSIGN', 'NAME', 'CITY', 'STATE', 'COUNTRY', 'TYPE')
PEER_FIELDS  = ('ID', 'CALLSIGN', 'CITY', 'STATE', 'COUNTRY', 'FREQ', 'CC', 'OFFSET', 'TYPE', 'LINKED', 'TRUSTEE', 'INFO', 'OTHER', 'NETWORK', )
TGID_FIELDS  = ('ID', 'NAME')

def hex_str_2(_int_id):
    return unhexlify(format(_int_id, 'x').zfill(4))

def hex_str_3(_int_id):
    return unhexlify(format(_int_id, 'x').zfill(6))

def hex_str_4(_int_id):
    return unhexlify(format(_int_id, 'x').zfill(8))

bytes_2 = hex_str_2
bytes_3 = hex_str_3
bytes_4 = hex_str_4

def int_id(_hex_string):
    if isinstance(_hex_string, str):
        _hex_string = _hex_string.encode('latin-1')
    return int(ahex(_hex_string), 16)

def try_download(_path, _file, _url, _stale):
    now = time()
    full_path = _path + _file
    file_exists = isfile(full_path)
    
    if file_exists:
        file_old = (getmtime(full_path) + _stale) < now
    
    if not file_exists or (file_exists and file_old):
        try:
            # Python 3 modernized download
            urllib.request.urlretrieve(_url, full_path)
            return "ID ALIAS MAPPER: '{}' successfully downloaded".format(_file)
        except Exception as e:
            return "ID ALIAS MAPPER: '{}' could not be downloaded".format(_file)
    else:
        return "ID ALIAS MAPPER: '{}' is current, not downloaded".format(_file)

def mk_id_dict(_path, _file):
    _dict = {}
    try:
        # Added errors='ignore' to handle non-UTF-8 subscriber names
        with open(_path + _file, 'r', encoding='utf-8', errors='ignore') as _handle:
            records = json.load(_handle)
            if 'count' in records:
                del records['count']
            
            # Python 3 compatible key indexing
            first_key = list(records.keys())[0]
            data_list = records[first_key]
            
            for record in data_list:
                try:
                    _dict[int(record['id'])] = record['callsign']
                except (KeyError, ValueError):
                    pass
        return _dict
    except (IOError, json.JSONDecodeError):
        return _dict

def mk_full_id_dict(_path, _file, _type):
    _dict = {}
    try:
        with open(_path + _file, 'r', encoding='utf-8', errors='ignore') as _handle:
            records = json.load(_handle)
            if 'count' in records:
                del records['count']
            
            first_key = list(records.keys())[0]
            data_list = records[first_key]

            for record in data_list:
                try:
                    rid = int(record['id'])
                    if _type == 'peer':
                        _dict[rid] = {'CALLSIGN': record.get('callsign'), 'CITY': record.get('city'), 'NETWORK': record.get('ipsc_network')}
                    elif _type == 'subscriber':
                        _dict[rid] = {
                            'CALLSIGN': record.get('callsign'),
                            'NAME': "{} {}".format(record.get('fname', ''), record.get('surname', '')).strip()
                        }
                except (KeyError, ValueError):
                    pass
        return _dict
    except (IOError, json.JSONDecodeError):
        return _dict

def get_alias(_id, _dict, *args):
    if isinstance(_id, (str, bytes)):
        try:
            _id = int_id(_id)
        except:
            pass
    return _dict.get(_id, _id)

get_info = get_alias